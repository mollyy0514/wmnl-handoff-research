#!/usr/bin/python3
### Filename: udp_analysis.py

"""
Classify packet loss by different handover types.

若 pcap, ho.csv 檔案為空:
    start_time = '-'
    end_time = '-'
    exp_time = 0

Author: Yuan-Jye Chen
Update: Yuan-Jye Chen 2022/10/14
"""

"""
    Future Development Plan
        (1) Neglect filename start with ".~lock". (e.g., ".~lock.packet_info.csv#", ".~lock.client_pcap_BL_sm05_3210_3211_2022-09-29_16-24-57.csv#")
        (2) focus 在 UE 端狀況，因此 timestamp 應取 expected arrival time (DL) 和 transmit time (UL)，目前都是取 expected arrival time。
    
"""
import os
import sys
import pandas as pd
import datetime as dt
import matplotlib.pyplot as plt
import numpy as np
# import intervals as I
import portion as P
import itertools as it
import csv
from pprint import pprint
from pytictoc import TicToc
from tqdm import tqdm
import traceback

# ******************************* User Settings *******************************
PKT_LEN = 250  # Bytes
DATA_RATE = 1000e3  # bits-per-second
PKT_RATE = DATA_RATE / PKT_LEN / 8  # packets-per-second
print("packet_rate (pps):", PKT_RATE, "\n")

database = "/home/wmnlab/D/database/"
date = "2022-10-20"
db_path = os.path.join(database, date)
Exp_Name = {  # experiment_name:(number_of_experiment_rounds, list_of_experiment_round)
                # If the list is empty, it will list all directories in the current directory by default.
                # If the number of experiment times != the length of existing directories of list, it would trigger warning and skip the directory.
    # "_Bandlock_Udp":(1, ["#01"]),
    # "_Bandlock_Udp":(5, ["#02", "#03", "#04", "#05", "#06"]),
    # "_Bandlock_Udp":(1, ["#02"]),
    # "_Bandlock_Udp":(1, ["#03"]),
    # "_Bandlock_Udp":(4, ["#01", "#02", "#03", "#04"]),
    # "_Bandlock_Udp":(6, []),
    # "_Bandlock_Udp":(4, []),
    "_Udp_Stationary_Bandlock":(1, []),
    "_Udp_Stationary_SameSetting":(1, []),
}
devices = sorted([
    # "sm03",
    "sm04",
    "sm05", 
    "sm06",
    "sm07",
    "sm08",
])
# *****************************************************************************

# --------------------- Util Functions ---------------------
### This function firstly generates three intervals for each [handover_start, handover_end] in handover_list
#   a. before the handover_start event: [handover_start-second, handover_start]
#   b. during the handover events: [handover_start, handover_end]
#   c. after the handover_end event: [handover_end, handover_end+second]
# Then, it returns the overall intervals before/during/after the handover event

def makedir(dirpath, mode=0):  # mode=1: show message, mode=0: hide message
    if os.path.isdir(dirpath):
        if mode:
            print("mkdir: cannot create directory '{}': directory has already existed.".format(dirpath))
        return
    ### recursively make directory
    _temp = []
    while not os.path.isdir(dirpath):
        _temp.append(dirpath)
        dirpath = os.path.dirname(dirpath)
    while _temp:
        dirpath = _temp.pop()
        print("mkdir", dirpath)
        os.mkdir(dirpath)

def interp(x, y, ratio):
    """
    Interpolation

    Args:
        x, y (datetime.datetime)
        ratio (float): a decimal numeral in a range [0, 1]
    Returns:
        (datetime.datetime): breakpoint of interpolation
    """
    return x + (y - x) * ratio

def is_disjoint(set1, set2):
    """
    Check if two sets are disjoint.
    """
    return (set1 & set2).empty

def all_disjoint(set_list):
    """
    Check if all sets in the list are pairwise disjoint.
    """
    pair_list = list(it.combinations(set_list, 2))
    for item in pair_list:
        if not is_disjoint(item[0], item[1]):
            return False
    return True

def all_union(set_list):
    """
    Union all set in the list.
    """
    _temp = P.empty()
    for _set in set_list:
        _temp = _temp | _set
    return _temp

def get_handover_intervals(df, event_names, secs=1, exp_time=(dt.datetime.min, dt.datetime.max), overlap=True, ratio=1):
    """
    Get intervals of each event type.

    Args:
        df (pandas.Dataframe): dataframe read from diag_log_ho-info.csv
        event_names (list): list of event types, it would include all spcified types together.
        secs (float): size of window that you need. (in seconds)
        exp_time (tuple): (start_time, end_time) of an experiment.
        overlap (bool): allows intervals to be overlapping or not.
        ratio (float): a decimal numeral in a range [0, 1], to decide the breakpoint of interpolation.

    Example. secs=1.2, ratio=0.8
        .                    (overlap)               (overlap)
    ----[------------)[.](--[----------]--)[x](-------[-----]-------)[.](------------]----> (sec)
        1.b            1    2.b      a.1    2         3.b a.2         3            a.3
        .
    ----[------------)[.](----------)[----)[x](-----------)[--------)[.](------------]----> (sec)
        1.b            1          a.12.b    2           a.23.b        3            a.3
        We assume the during events of each type do not overlap, the previous or next handover state would only be the following,
        .] : 'end' or 'trigger'
        [x]: 'start'-'end' pair or 'trigger
        [. : 'start' or 'trigger
        'a' means "after_event", 'b' means "before_event"
    
    Extreme Case (1). secs=1.2, ratio=0 (before/prior case)
        .
    ----[--------[----)   [.]   (--------)   [x]   (----]--------]----> (sec)
        1.b      2.b       1                  2       a.1      a.2
        .        |(bp)          |(.])
    ----[-------- ----)   [.] ()(--------)   [x]   (---- --------]----> (sec)
        1.b                1 a.12.b           2                a.2
        take max{ bp & .] } as left-bound, a.1 would be empty()
        'a' means "after_event", 'b' means "before_event"
    
    Extreme Case (2). secs=1.2, ratio=1 (after/post case)
    .
    ----[--------[----)   [x]   (--------)   [.]   (----]--------]----> (sec)
        1.b      2.b       1                  2       a.1      a.2
        .                                |([.)          |(bp)
    ----[-------- ----)   [x]   (--------)() [.]   (---- --------]----> (sec)
        1.b                1           a.12.b 2                a.2
        take min{ bp & [. } as right-bound, 2.b would be empty()
        'a' means "after_event", 'b' means "before_event"

    Returns:
        before_event_intervals (portion.interval.Interval)
        during_events_intervals (portion.interval.Interval)
        after_events_intervals (portion.interval.Interval)
    """
    before_events_intervals = P.empty()
    during_events_intervals = P.empty()
    after_events_intervals = P.empty()
    _prior_interval = P.empty()
    _midd_interval = P.empty()
    _post_interval = P.empty()
    # print(df)
    anomaly_check = []
    for i in range(len(df)):
        # print(i+2)
        if df.loc[i, 'handoff_type'] in event_names:
            if df.loc[i, 'handoff_state'] == 'start':
                ### before
                _start = df.iloc[i]
                prior_interval = P.closedopen( max(_start['Timestamp'] - dt.timedelta(seconds=secs), exp_time[0]), min(_start['Timestamp'], exp_time[1]) )
                if not overlap and i != 0 and (df.loc[i-1, 'Timestamp'] + dt.timedelta(seconds=secs) in prior_interval or df.loc[i-1, 'Timestamp'] in prior_interval):
                # if not overlap and i not in [0, len(df)-1] and (df.loc[i-1, 'Timestamp'] + dt.timedelta(seconds=secs) in prior_interval or df.loc[i-1, 'Timestamp'] in prior_interval):
                    # print(i+2, "start prior overlap")
                    breakpoint = interp(_start['Timestamp'] - dt.timedelta(seconds=secs), df.loc[i-1, 'Timestamp'] + dt.timedelta(seconds=secs), ratio)
                    breakpoint = max(breakpoint, df.loc[i-1, 'Timestamp'])
                    ### All open is fine, but sometimes may miss one point.
                    prior_interval = P.closedopen( max(breakpoint, exp_time[0]), min(_start['Timestamp'], exp_time[1]) )
                    if df.loc[i-1, 'Timestamp'] in prior_interval:
                        prior_interval = P.open( max(breakpoint, exp_time[0]), min(_start['Timestamp'], exp_time[1]) )
                before_events_intervals = before_events_intervals | prior_interval
                ### Exception: during, after
                if i == len(df)-1:
                    midd_interval = P.closed( max(_start['Timestamp'], exp_time[0]), exp_time[1] )
                    during_events_intervals = during_events_intervals | midd_interval
                    post_interval = P.empty()
                    after_events_intervals = after_events_intervals | post_interval
            elif df.loc[i, 'handoff_state'] == 'end':
                ### Exception: before
                if i == 0:
                    prior_interval = P.empty()
                    before_events_intervals = before_events_intervals | prior_interval
                    _start = pd.Series({"Timestamp":exp_time[0], "type_id":'-', "handoff_type":'-', "handoff_state":'-', "handoff_duration":'-', "PCI":'-', "EARFCN":'-', "NR_PCI":'-', "NR_ARFCN":'-'})
                ### during
                midd_interval = P.closed( max(_start['Timestamp'], exp_time[0]), min(df.loc[i, 'Timestamp'], exp_time[1]) )
                during_events_intervals = during_events_intervals | midd_interval
                ### after
                post_interval = P.openclosed( max(df.loc[i, 'Timestamp'], exp_time[0]), min(df.loc[i, 'Timestamp'] + dt.timedelta(seconds=secs), exp_time[1]) )
                if not overlap and i != len(df)-1 and (df.loc[i+1, 'Timestamp'] - dt.timedelta(seconds=secs) in post_interval or df.loc[i+1, 'Timestamp'] in post_interval):
                # if not overlap and i not in [0, len(df)-1] and (df.loc[i+1, 'Timestamp'] - dt.timedelta(seconds=secs) in post_interval or df.loc[i+1, 'Timestamp'] in post_interval):
                    # print(i+2, "end post overlap")
                    breakpoint = interp(df.loc[i+1, 'Timestamp'] - dt.timedelta(seconds=secs), df.loc[i, 'Timestamp'] + dt.timedelta(seconds=secs), ratio)
                    breakpoint = min(breakpoint, df.loc[i+1, 'Timestamp'])
                    post_interval = P.open( max(df.loc[i, 'Timestamp'], exp_time[0]), min(breakpoint, exp_time[1]) )
                after_events_intervals = after_events_intervals | post_interval
            elif df.loc[i, 'handoff_state'] == 'trigger':
                if i != 0 and df.loc[i-1, 'handoff_state'] == 'start':
                    # prior_interval = P.empty()
                    # post_interval = P.empty()
                    print("*******************************************************************")
                    print(df.loc[i, 'Timestamp'])
                    print("Link failure occurs during handover duration: {}".format(df.loc[i, 'handoff_type']))
                    print("Prior event: {} {}".format(df.loc[i-1, 'handoff_type'], df.loc[i-1, 'handoff_state']))
                    anomaly_check.append((df.loc[i, 'Timestamp'], df.loc[i, 'handoff_type'], df.loc[i-1, 'handoff_type']))
                    continue
                ### before
                prior_interval = P.closedopen( max(df.loc[i, 'Timestamp'] - dt.timedelta(seconds=secs), exp_time[0]), min(df.loc[i, 'Timestamp'], exp_time[1]) )
                if not overlap and i != 0 and (df.loc[i-1, 'Timestamp'] + dt.timedelta(seconds=secs) in prior_interval or df.loc[i-1, 'Timestamp'] in prior_interval):
                # if not overlap and i not in [0, len(df)-1] and (df.loc[i-1, 'Timestamp'] + dt.timedelta(seconds=secs) in prior_interval or df.loc[i-1, 'Timestamp'] in prior_interval):
                    # print(i+2, "trigger prior overlap")
                    breakpoint = interp(df.loc[i, 'Timestamp'] - dt.timedelta(seconds=secs), df.loc[i-1, 'Timestamp'] + dt.timedelta(seconds=secs), ratio)
                    breakpoint = max(breakpoint, df.loc[i-1, 'Timestamp'])
                    ### All open is fine, but sometimes may miss one point.
                    prior_interval = P.closedopen( max(breakpoint, exp_time[0]), min(df.loc[i, 'Timestamp'], exp_time[1]) )
                    if df.loc[i-1, 'Timestamp'] in prior_interval:
                        prior_interval = P.open( max(breakpoint, exp_time[0]), min(df.loc[i, 'Timestamp'], exp_time[1]) )
                before_events_intervals = before_events_intervals | prior_interval
                ### during
                midd_interval = P.singleton( df.loc[i, 'Timestamp'] )
                during_events_intervals = during_events_intervals | midd_interval
                ### after
                post_interval = P.openclosed( max(df.loc[i, 'Timestamp'], exp_time[0]), min(df.loc[i, 'Timestamp'] + dt.timedelta(seconds=secs), exp_time[1]) )
                # print('******************************************************')
                # print(df.loc[i, 'handoff_type'], df.loc[i, 'handoff_state'], df.loc[i, 'Timestamp'])
                # print(df.loc[i+1, 'handoff_type'], df.loc[i+1, 'handoff_state'], df.loc[i+1, 'Timestamp'])
                # print('******************************************************')
                if not overlap and i != len(df)-1 and (df.loc[i+1, 'Timestamp'] - dt.timedelta(seconds=secs) in post_interval or df.loc[i+1, 'Timestamp'] in post_interval):
                # if not overlap and i not in [0, len(df)-1] and (df.loc[i+1, 'Timestamp'] - dt.timedelta(seconds=secs) in post_interval or df.loc[i+1, 'Timestamp'] in post_interval):
                    # print(i+2, "trigger post overlap")
                    breakpoint = interp(df.loc[i+1, 'Timestamp'] - dt.timedelta(seconds=secs), df.loc[i, 'Timestamp'] + dt.timedelta(seconds=secs), ratio)
                    breakpoint = min(breakpoint, df.loc[i+1, 'Timestamp'])
                    post_interval = P.open( max(df.loc[i, 'Timestamp'], exp_time[0]), min(breakpoint, exp_time[1]) )
                after_events_intervals = after_events_intervals | post_interval

            # if df.loc[i, 'handoff_state'] == 'end' or df.loc[i, 'handoff_state'] == 'trigger':
            #     set1 = _prior_interval | _midd_interval | _post_interval
            #     set2 = prior_interval | midd_interval | post_interval
            #     # if not is_disjoint(set1, set2) or i+2 == 7:
            #     if not is_disjoint(set1, set2):
            #         print(False, i+2)
            #         print("-------------------------------------")
            #         print("previous:      ", set1)
            #         print("previous prior:", _prior_interval, is_disjoint(_prior_interval, set2))
            #         print("previous midd: ", _midd_interval, is_disjoint(_midd_interval, set2))
            #         print("previous post: ", _post_interval, is_disjoint(_post_interval, set2))
            #         print("-------------------------------------")
            #         print("current:       ", set2)
            #         print("current prior: ", prior_interval, is_disjoint(prior_interval, set1))
            #         print("current midd:  ", midd_interval, is_disjoint(midd_interval, set1))
            #         print("current post:  ", post_interval, is_disjoint(post_interval, set1))
            #         print("-------------------------------------")
            #     _prior_interval = prior_interval
            #     _midd_interval = midd_interval
            #     _post_interval = post_interval

    return before_events_intervals, during_events_intervals, after_events_intervals, anomaly_check

def get_intervals_length(intervals):
    """
    Get total length of a set of intervals.
    """
    if intervals.empty:
        return 0
    sum = 0
    for s in intervals:
        sum += (s.upper - s.lower) / dt.timedelta(seconds=1)
    return round(sum, 6)

def ho_statistics(lossdf, recvdf, hodf, fout):
    hodf.loc[:, 'Timestamp'] = pd.to_datetime(hodf.loc[:, 'Timestamp'])
    lossdf.loc[:, 'Timestamp'] = pd.to_datetime(lossdf.loc[:, 'Timestamp'])
    lossdf.loc[:, 'payload.time'] = pd.to_datetime(lossdf.loc[:, 'payload.time'])
    recvdf.loc[:, 'Timestamp'] = pd.to_datetime(recvdf.loc[:, 'Timestamp'])
    recvdf.loc[:, 'payload.time'] = pd.to_datetime(recvdf.loc[:, 'payload.time'])
    if len(lossdf):
        start_time = min(recvdf['Timestamp'].iloc[0], lossdf['Timestamp'].iloc[0])
        end_time = max(recvdf['Timestamp'].iloc[-1], lossdf['Timestamp'].iloc[-1])
    else:  # if there is no packet loss.
        ### !!! 假如一開始就掉封包，目前設定是 arrival.time == '-'，可能會出問題（之後可能要改成外插比較安全）
        start_time = recvdf['Timestamp'].iloc[0] if len(recvdf) else dt.datetime.min
        end_time = recvdf['Timestamp'].iloc[-1] if len(recvdf) else dt.datetime.max
    exp_time = (end_time - start_time).total_seconds() if len(recvdf) else 0
    
    if len(hodf):
        start_indices = hodf.index[hodf['Timestamp'] >= start_time]
        end_indices = hodf.index[hodf['Timestamp'] <= end_time]
        if len(start_indices) and len(end_indices):
            start_index = start_indices[0]
            end_index = end_indices[-1]
        else:
            hodf = hodf.iloc[0:0]
        try:
            if hodf.loc[start_index, 'handoff_state'] == 'end':
                hodf.loc[start_index - 1, 'Timestamp'] = start_time
                start_index -= 1
            if hodf.loc[end_index, 'handoff_state'] == 'start':
                hodf.loc[end_index + 1, 'Timestamp'] = end_time
                end_index += 1
            hodf = hodf.iloc[start_index : end_index + 1]
        except:
            pass
        hodf = hodf[hodf['handoff_state'] != 'end']
        hodf = hodf.reset_index(drop=True)

    event_names = "lte_handover,SN_addition,SN_removal,endc_SN_change,endc_MN_change,endc_MNSN_change,lte2endc_MN_change,endc2lte_MN_change,scg_failure,radio_link_failure,nas_recovery".split(',')
    ss = [0] * len(event_names)
    for i, item in enumerate(event_names):
        ss[i] = sum(hodf['handoff_type'] == item)
    ss.append(sum(ss[:8]))
    ss.append(sum(ss[8:11]))
    ss.append(sum(ss[:11]))
    ss.append(exp_time)
    event_names += ["succ_handoff", "fail_handoff", "overall_handoff", "experiment_time(sec)"]
    with open(fout, "w", newline='') as fp:
        writer = csv.writer(fp)
        writer.writerow(event_names)
        writer.writerow(ss)

def packet_ho_classify(hodf, lossdf, recvdf, fout, secs=1, overlap=True, ratio=1):
    anomaly_check_list = []
    hodf.loc[:, 'Timestamp'] = pd.to_datetime(hodf.loc[:, 'Timestamp'])
    lossdf.loc[:, 'Timestamp'] = pd.to_datetime(lossdf.loc[:, 'Timestamp'])
    lossdf.loc[:, 'payload.time'] = pd.to_datetime(lossdf.loc[:, 'payload.time'])
    recvdf.loc[:, 'Timestamp'] = pd.to_datetime(recvdf.loc[:, 'Timestamp'])
    recvdf.loc[:, 'payload.time'] = pd.to_datetime(recvdf.loc[:, 'payload.time'])
    if len(lossdf):
        start_time = min(recvdf['Timestamp'].iloc[0], lossdf['Timestamp'].iloc[0])
        end_time = max(recvdf['Timestamp'].iloc[-1], lossdf['Timestamp'].iloc[-1])
    else:  # if there is no packet loss.
        ### !!! 假如一開始就掉封包，目前設定是 arrival.time == '-'，可能會出問題（之後可能要改成外插比較安全）
        start_time = recvdf['Timestamp'].iloc[0] if len(recvdf) else '-'
        end_time = recvdf['Timestamp'].iloc[-1] if len(recvdf) else '-'
    exp_time = (end_time - start_time).total_seconds() if len(recvdf) else 0
    
    if len(hodf):
        hodf = hodf[(hodf['Timestamp'] >= start_time) & (hodf['Timestamp'] <= end_time)]
        hodf = hodf.reset_index(drop=True)
    # print("*****************************************")
    # print("start_time:", start_time)
    # print("end_time:", end_time)
    # print("experiment_time:", exp_time)
    # print("-----------------------------")
    # print("window (sec)?", secs)
    # print("allow overlapping?", "yes" if overlap else "no")
    # print("clash ratio?", ratio)

    handover_type_names = "lte_handover, SN_addition, SN_removal, endc_SN_change, endc_MN_change, endc_MNSN_change, lte2endc_MN_change, endc2lte_MN_change".split(', ')
    failure_type_names = "scg_failure, radio_link_failure, nas_recovery".split(', ')

    column_names = []
    for type_name in handover_type_names:
        column_names += ["before_{}".format(type_name), "during_{}".format(type_name), "after_{}".format(type_name)]
    for type_name in failure_type_names:
        column_names += ["before_{}".format(type_name), "after_{}".format(type_name)]
    column_names += ["before_succ_handoff", "during_succ_handoff", "after_succ_handoff", "before_fail_handoff", "after_fail_handoff", "unstable", "stable", "overall"]

    event_occurrence = [0] * len(column_names)
    sum_total_time = [0] * len(column_names)
    sum_total_num = [0] * len(column_names)
    sum_loss_num = [0] * len(column_names)
    loss_rate = [0] * len(column_names)

    all_intervals = []

    offset = len(handover_type_names) * 3
    for i, event_type in enumerate(handover_type_names):
        before_intervals, during_intervals, after_intervals, anomaly_check = get_handover_intervals(hodf, [event_type], secs=secs, exp_time=(start_time, end_time), overlap=overlap, ratio=ratio)
        # print(event_type)
        # print(before_intervals)
        # print(during_intervals)
        # print(after_intervals)
        all_intervals.append(before_intervals)
        all_intervals.append(during_intervals)
        all_intervals.append(after_intervals)
        event_occurrence[3*i] = event_occurrence[3*i+1] = event_occurrence[3*i+2] = len(hodf[(hodf['handoff_type'] == event_type) & (hodf['handoff_state'] != 'end')])
        if anomaly_check:
            anomaly_check_list.append(anomaly_check)
    for i, event_type in enumerate(failure_type_names):
        before_intervals, during_intervals, after_intervals, anomaly_check = get_handover_intervals(hodf, [event_type], secs=secs, exp_time=(start_time, end_time), overlap=overlap, ratio=ratio)
        # print(event_type)
        # print(before_intervals)
        # print(during_intervals)
        # print(after_intervals)
        all_intervals.append(before_intervals | during_intervals)
        all_intervals.append(after_intervals)
        event_occurrence[2*i+offset] = event_occurrence[2*i+offset+1] = len(hodf[(hodf['handoff_type'] == event_type) & (hodf['handoff_state'] != 'end')])
        if anomaly_check:
            anomaly_check_list.append(anomaly_check)
    print("disjoint set?", "yes!" if all_disjoint(all_intervals) else "no!")
    print("-----------------------------")

    all_intervals.append(all_union(all_intervals[:24:3]))
    all_intervals.append(all_union(all_intervals[1:24:3]))
    all_intervals.append(all_union(all_intervals[2:24:3]))
    all_intervals.append(all_union(all_intervals[24:30:2]))
    all_intervals.append(all_union(all_intervals[25:30:2]))
    all_intervals.append(all_union(all_intervals[:30]))
    all_intervals.append(P.closed(start_time, end_time) - all_intervals[-1] if len(recvdf) else P.empty())
    all_intervals.append(P.closed(start_time, end_time) if len(recvdf) else P.empty())

    loss_timestamps = lossdf['Timestamp'].array
    for i, item in enumerate(all_intervals):
        sum_total_time[i] = get_intervals_length(item)
        sum_total_num[i] = round(sum_total_time[i] * PKT_RATE)
        for j in range(len(lossdf)):
            if item.empty:
                break
            # if lossdf['Timestamp'].iloc[j] > item.upper:
            if loss_timestamps[j] > item.upper:
                break
            # if lossdf['Timestamp'].iloc[j] in item:
            if loss_timestamps[j] in item:
                sum_loss_num[i] += 1
        
        ### 絕無誤差的計算 sent_packet 數量的方式（取消註解即可）
        # sum_total_num[i] = 0
        # for j in range(len(recvdf)):
        #     if item.empty:
        #         break
        #     if recvdf['Timestamp'].iloc[j] > item.upper:
        #         break
        #     if recvdf['Timestamp'].iloc[j] in item:
        #         sum_total_num[i] += 1
        # sum_total_num[i] += sum_loss_num[i]

        loss_rate[i] = sum_loss_num[i] / (sum_total_num[i] + 1e-9) * 100
    event_occurrence[-6] = event_occurrence[-7] = event_occurrence[-8] = sum(event_occurrence[:24:3])  # successful handoff
    event_occurrence[-4] = event_occurrence[-5] = sum(event_occurrence[24:30:2])  # failed handoff
    event_occurrence[-3] = event_occurrence[-5] + event_occurrence[-8]  # all handoff (unstable)
    event_occurrence[-1] = event_occurrence[-2] = '-'  # stable & overall

    # print(column_names)
    # print(event_occurrence)
    # print(sum_total_time)
    # print(sum_total_num)
    # print(sum_loss_num)
    # print(loss_rate)

    column_names = ["type"] + column_names
    event_occurrence = ["occurrence"] + event_occurrence
    sum_total_time = ["total_duration"] + sum_total_time
    sum_total_num = ["total_packet_num"] + sum_total_num
    sum_loss_num = ["packet_loss_num"] + sum_loss_num
    loss_rate = ["packet_loss_rate(%)"] + loss_rate

    print("output >>>", fout)
    with open(fout, "w", newline='') as fp:
        writer = csv.writer(fp)
        for item in zip(column_names, event_occurrence, sum_total_time, sum_total_num, sum_loss_num, loss_rate):
            writer.writerow(item)
    
    return anomaly_check_list


if __name__ == "__main__":
    anomaly_detect_list = []
    t = TicToc()  # create instance of class
    t.tic()  # Start timer
    # --------------------- (3) decode a batch of files (User Settings) ---------------------
    for _exp, (_times, _rounds) in Exp_Name.items():
        ### Check if these directories exist
        exp_path = os.path.join(db_path, _exp)
        print(exp_path)
        exp_dirs = []
        for i, dev in enumerate(devices):
            if _rounds:
                exp_dirs.append([os.path.join(exp_path, dev, _round) for _round in _rounds])
            else:
                _rounds = sorted(os.listdir(os.path.join(exp_path, dev)))
                exp_dirs.append([os.path.join(exp_path, dev, item) for item in _rounds])
            exp_dirs[i] = [item for item in exp_dirs[i] if os.path.isdir(item)]
            print(_times)
            pprint(exp_dirs[i])
            if len(exp_dirs[i]) != _times:
                print("************************************************************************************************")
                print("Warning: the number of directories does not match your specific number of experiment times.")
                print("************************************************************************************************")
                print()
                sys.exit()
        print()

        # --------------------- Downlink --------------------- 
        ### server_DL (Tx), client_DL (Rx)

        ### Read files
        print(_exp)
        for j in range(_times):
            for i, dev in enumerate(devices):
                print(exp_dirs[i][j])
                dirpath = os.path.join(exp_dirs[i][j], "analysis")
                makedir(os.path.join(dirpath, "udp-loss-classify-50p"))  # 0.5 == 50 percent
                hodf = pd.read_csv(os.path.join(dirpath, "diag_log_ho-info.csv"))
                lossdf = pd.read_csv(os.path.join(dirpath, "dwnlnk_udp_loss_timestamp.csv"))
                # recvdf = pd.read_csv(os.path.join(dirpath, "clt_dwnlnk_udp_packet_brief.csv"))
                recvdf = pd.read_csv(os.path.join(dirpath, "dwnlnk_udp_latency.csv"))
                fout = os.path.join(dirpath, "udp-loss-classify-50p", "dwnlnk_ho_statistics.csv")
                ho_statistics(lossdf, recvdf, hodf, fout)
                for i in tqdm(range(10)):
                    fout = os.path.join(dirpath, "udp-loss-classify-50p", "dwnlnk_loss_ho_classify_0{}.csv".format(i))
                    anomaly_check_list = packet_ho_classify(hodf.copy(), lossdf.copy(), recvdf.copy(), fout, secs=i/10, overlap=False, ratio=0.5)
                    if i == 0 and anomaly_check_list:
                        anomaly_detect_list.append((os.path.join(dirpath, "diag_log_ho-info.csv"), anomaly_check_list))
                for i in tqdm(range(1, 11)):
                    fout = os.path.join(dirpath, "udp-loss-classify-50p", "dwnlnk_loss_ho_classify_{}.csv".format(i))
                    packet_ho_classify(hodf.copy(), lossdf.copy(), recvdf.copy(), fout, secs=i, overlap=False, ratio=0.5)
                print()

                ### test for only one data
                # sys.exit()

        # --------------------- Uplink --------------------- 
        ### server_UL (Rx), client_UL (Tx)

        ### Read files
        print(_exp)
        for j in range(_times):
            for i, dev in enumerate(devices):
                print(exp_dirs[i][j])
                dirpath = os.path.join(exp_dirs[i][j], "analysis")
                makedir(os.path.join(dirpath, "udp-loss-classify-50p"))  # 0.5 == 50 percent
                hodf = pd.read_csv(os.path.join(dirpath, "diag_log_ho-info.csv"))
                lossdf = pd.read_csv(os.path.join(dirpath, "uplnk_udp_loss_timestamp.csv"))
                # recvdf = pd.read_csv(os.path.join(dirpath, "srv_uplnk_udp_packet_brief.csv"))
                recvdf = pd.read_csv(os.path.join(dirpath, "uplnk_udp_latency.csv"))
                fout = os.path.join(dirpath, "udp-loss-classify-50p", "uplnk_ho_statistics.csv")
                ho_statistics(lossdf, recvdf, hodf, fout)
                for i in tqdm(range(10)):
                    fout = os.path.join(dirpath, "udp-loss-classify-50p", "uplnk_loss_ho_classify_0{}.csv".format(i))
                    packet_ho_classify(hodf.copy(), lossdf.copy(), recvdf.copy(), fout, secs=i/10, overlap=False, ratio=0.5)
                for i in tqdm(range(1, 11)):
                    fout = os.path.join(dirpath, "udp-loss-classify-50p", "uplnk_loss_ho_classify_{}.csv".format(i))
                    packet_ho_classify(hodf.copy(), lossdf.copy(), recvdf.copy(), fout, secs=i, overlap=False, ratio=0.5)
                print()
    for item in anomaly_detect_list:
        print(item[0])
        pprint(item[1])
    print()
    t.toc()  # Time elapsed since t.tic()
