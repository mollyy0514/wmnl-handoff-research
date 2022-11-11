#!/usr/bin/python3
### Filename: udp_analysis.py

"""
Analyze packet capture of udp experiments.
Need to convert .pcap into .csv by tshark with script udp_pcap_to_csv.py

若 pcap, ho.csv 檔案為空:
    start_time = '-'
    end_time = '-'
    exp_time = 0

Author: Yuan-Jye Chen
Update: Yuan-Jye Chen 2022/10/09
"""

"""
    Future Development Plan
        (1) Neglect filename start with ".~lock". (e.g., ".~lock.packet_info.csv#", ".~lock.client_pcap_BL_sm05_3210_3211_2022-09-29_16-24-57.csv#")
        (2) Output packet loss statistics and lanency.
        (3) Time synchronization. (preprocessing)
        (4) functionalize
        (5) 對一下 packet loss rate / packet loss number 是否與截圖 summary 相符
        (6) 若一開始就掉封包，建議改成外插法預測！
        (7) focus 在 UE 端狀況，因此 timestamp 應取 expected arrival time (DL) 和 transmit time (UL)，目前都是取 expected arrival time。
        (8) readline of csv 逐行（不要一次 handle 整個 dataframe，因為 payload 太長，RAM 會爆掉），目前先把 rxdf, txdf 分別處理，不要兩個都讀進來才處理（30min-500pps-pcap.csv 還夠用）
    
"""
import os
import sys
import argparse
import csv
import pandas as pd
import datetime as dt
import numpy as np
from pprint import pprint
from tqdm import tqdm
from pytictoc import TicToc
import traceback
from statistics import median
from statistics import mean
from statistics import mode
from statistics import stdev
from scipy import stats
from scipy import signal
import portion as P

# ******************************* User Settings *******************************
class Payload:
    LENGTH = 250              # (Bytes)
    TAG = "000425d401df5e76"  # 2 71828 3 1415926 (hex)            : 8-bytes
    OFS_TIME = (16, 24)       # epoch time of 'yyyy/mm/dd hh:mm:ss': 4-bytes
    OFS_USEC = (24, 32)       # microsecond (usec)                 : 4-bytes
    OFS_SEQN = (32, 40)       # sequence number (start from 1)     : 4-bytes
class ServerIP:
    PUBLIC = "140.112.20.183"  # 2F    
    PRIVATE = "192.168.1.248"  # 2F
    # PUBLIC = "140.112.17.209"  # 3F
    # PRIVATE = "192.168.1.108"  # 3F

DATA_RATE = 1000e3  # bits-per-second
PKT_RATE = DATA_RATE / Payload.LENGTH / 8  # packets-per-second
print("packet_rate (pps):", PKT_RATE, "\n")

database = "/home/wmnlab/D/database/"
date = "2022-10-20"
db_path = os.path.join(database, date)
Exp_Name = {  # experiment_name:(number_of_experiment_rounds, list_of_experiment_round)
                # If the list is empty, it will list all directories in the current directory by default.
                # If the number of experiment times != the length of existing directories of list, it would trigger warning and skip the directory.
    # "_Bandlock_Udp":(1, ["#01"]),
    # "_Bandlock_Udp":(1, ["#06"]),
    # "_Bandlock_Udp":(5, ["#02", "#03", "#04", "#05", "#06"]),
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

# --------------------- Global Variables ---------------------
TRANS = 4
RECV = 0
TCP = 6
UDP = 17

# --------------------- Util Functions ---------------------
def t_mean(timedeltas):
    """
    Average of a list of timedelta.
    """
    return sum(timedeltas, dt.timedelta(0)) / len(timedeltas) if len(timedeltas) else 0

def truncate(txdf, rxdf):
    """
    Truncate the rows of lost packets.
    """
    tx_arr = list(zip(txdf['sequence.number'].array, txdf['Timestamp'].array, txdf['Timestamp_epoch'].array))
    rx_arr = list(zip(rxdf['sequence.number'].array, rxdf['Timestamp'].array, rxdf['Timestamp_epoch'].array))
    _tx_arr = []
    j = 0
    N = len(rx_arr)
    for i in range(len(tx_arr)):
        if tx_arr[i][0] == rx_arr[j][0]:
            _tx_arr.append(tx_arr[i])
            if j < N-1:
                j += 1
    ### Since the transmission is stopped by client,
    ### the ending sequence of Downlink-Tx/Uplink-Rx (Server-Side) is larger than Downlink-Rx/Uplink-Tx (Client-Side).
    M = min(len(_tx_arr), len(rx_arr))
    return _tx_arr[:M], rx_arr[:M]

def del_outliers(num_list):
    """
    Remove outliers and return the remaining list.
    """
    if not len(num_list):
        return [], []
    
    _num_list = sorted(num_list)
    upper_q = np.percentile(_num_list, 75)
    lower_q = np.percentile(_num_list, 25)
    iqr = (upper_q - lower_q) * 1.5
    q_set = (lower_q - iqr, upper_q + iqr)
    # print(q_set)

    result_list = []
    ret_list = []
    for i, x in enumerate(_num_list):
        if x >= q_set[0] and x <= q_set[1]:
            result_list.append(x)
            ret_list.append(i)
    
    return result_list, ret_list

def calc_delta(txdl_df, rxdl_df, txul_df, rxul_df):
    """
    Calculate the time delta between server and client.
        If the client is behind server, delta > 0
        If the client is ahead of server, delta < 0
        server clock := client clock + delta
        
    Returns:
        delta (datetime.timedelta)
        delta (float)
    """
    ### Since the transmission is launched by client, the starting time of Uplink is ahead of Downlink.
    seq_diff = round(500e-3 * PKT_RATE)
    txul_df = txul_df[txul_df['sequence.number'] > seq_diff].reset_index(drop=True)
    rxul_df = rxul_df[rxul_df['sequence.number'] > seq_diff].reset_index(drop=True)
    
    txdl_arr, rxdl_arr = truncate(txdl_df, rxdl_df)
    txul_arr, rxul_arr = truncate(txul_df, rxul_df)

    M = min(len(txdl_arr), len(txul_arr))
    txdl_arr, rxdl_arr, txul_arr, rxul_arr = txdl_arr[:M], rxdl_arr[:M], txul_arr[:M], rxul_arr[:M]

    epoch_delta_list = []
    for ts1, ts2, ts3, ts4 in zip(txdl_arr, rxdl_arr, txul_arr, rxul_arr):
        epoch_latency_dl = ts2[2] - ts1[2]
        epoch_latency_ul = ts4[2] - ts3[2]
        epoch_delta_list.append((epoch_latency_ul - epoch_latency_dl) / 2)
    
    # print(type(pd.Timedelta(microseconds=10)))  # <class 'pandas._libs.tslibs.timedeltas.Timedelta'> : datetime64[ns]
    # print(type(dt.timedelta(microseconds=10)))  # <class 'datetime.timedelta'> : microseconds

    if not len(epoch_delta_list):
        epoch_delta = [0, 0]
        timedelta = [pd.Timedelta(seconds=0), pd.Timedelta(seconds=0)]
        return timedelta, epoch_delta
    
    epoch_delta_list, _ = del_outliers(epoch_delta_list)

    kde = stats.gaussian_kde(epoch_delta_list)
    xx = np.linspace(min(epoch_delta_list), max(epoch_delta_list), 1000)
    yy = kde(xx)
    max_index = list(signal.argrelextrema(yy, np.greater)[0])
    stdev_1 = P.closed(mean(epoch_delta_list) - stdev(epoch_delta_list), mean(epoch_delta_list) + stdev(epoch_delta_list))
    _stdev =  stdev(epoch_delta_list)
    
    epoch_deltas = [xx[i] for i in max_index if xx[i] in stdev_1] + [mean(epoch_delta_list), median(epoch_delta_list), mode(epoch_delta_list)]
    # epoch_delta = [round(max(epoch_deltas), 6), round(min(epoch_deltas), 6)]
    # epoch_delta = [round(1.05 * max(epoch_deltas), 6), round(0.95 * min(epoch_deltas), 6)]
    # epoch_delta = [round(1.03 * max(epoch_deltas), 6), round(0.97 * min(epoch_deltas), 6)]
    epoch_delta = [round(max(epoch_deltas) + 1.15 * _stdev, 6), round(min(epoch_deltas) - 1.15 * _stdev, 6)]
    timedelta = [pd.Timedelta(seconds=secs).round('us') for secs in epoch_delta]
    print(timedelta)
    print(epoch_delta)

    ### Use mean, median, or mode: https://www.scribbr.com/statistics/central-tendency/
    ### Pandas.Timedelta: https://pandas.pydata.org/docs/reference/api/pandas.Timedelta.html
    ### Pandas.Timedelta.round: https://pandas.pydata.org/docs/reference/api/pandas.Timedelta.round.html
    return timedelta, epoch_delta

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

def error_handling(err_handle):
    """
    Print the error messages during the process.
    
    Args:
        err_handle (str-tuple): (input_filename, output_filename, error_messages : traceback.format_exc())
    Returns:
        (bool): check if the error_messages occurs, i.e., whether it is None.
    """
    if err_handle[2]:
        print()
        print("**************************************************")
        print("File decoding from '{}' into '{}' was interrupted.".format(err_handle[0], err_handle[1]))
        print()
        print(err_handle[2])
        return True
    return False

def to_utc8(ts):
    """
    Convert an epoch time into a readable format.
    Switch from utc-0 into utc-8.
    
    Args:
        ts (float): timestamp composed of datetimedec + microsecond (e.g., 1644051509.989306)
    Returns:
        (datetime.datetime): a readable timestamp (utc-8)
    """
    return (dt.datetime.utcfromtimestamp(ts) + dt.timedelta(hours=8))

def str_to_datetime(ts):
    """
    Convert a timestamp string in microseconds or milliseconds into datetime.datetime

    Args:
        ts (str): timestamp string (e.g., 2022-09-29 16:24:58.252615)
    Returns:
        (datetime.datetime)
    """
    try:
        ts_datetime = dt.datetime.strptime(ts, '%Y-%m-%d %H:%M:%S.%f')
    except:
        ts_datetime = dt.datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
    return ts_datetime

def datetime_to_str(ts):
    """
    Convert a datetime timestamp in microseconds into str

    Args:
        ts (datetime.datetime): datetime timestamp (e.g., datetime.datetime(2022, 9, 29, 16, 24, 58, 252615))
    Returns:
        (str): timestamp string (e.g., 2022-09-29 16:24:58.252615)
    """
    try:
        ts_string = dt.datetime.strftime(ts, '%Y-%m-%d %H:%M:%S.%f')
    except:
        ts_string = dt.datetime.strftime(ts, '%Y-%m-%d %H:%M:%S')
    return ts_string

def filter(df, terminal, direction, protocol):
    """
    Filter out the content that you need.

    Args:
        df (pandas.Dataframe): Original dataframe
        terminal  (str)      : 'server' or 'client'
        direction (str)      : 'uplink' or 'downlink'
        protocol  (str)      : 'tcp' or 'udp'
    Returns:
        df (pandas.Dataframe): Filtered dataframe
    """
    ### Convert frame.time into datetime
    try:
        df['frame.time'] = pd.to_datetime(df['frame.time']).dt.tz_localize(None)  # to remove the time zone information while keeping the local time
        # df['frame.time'] = pd.to_datetime(df['frame.time'])  # to remove the time zone information while keeping the local time
        # # with pd.option_context('display.max_rows', None):
        # #     print(df['frame.time'])
        # df['frame.time'] = df['frame.time'].dt.tz_localize(None)
    except:
        print(traceback.format_exc())
        sys.exit(1)

    ### UpLink or DownLink
    if terminal == 'client':
        if direction == 'uplink':
            # condition1 = df['sll.pkttype'] == TRANS
            df = df[df['sll.pkttype'] == TRANS]
        elif direction == 'downlink':
            # condition1 = df['sll.pkttype'] == RECV
            df = df[df['sll.pkttype'] == RECV]
    elif terminal == 'server':
        if direction == 'downlink':
            # condition1 = df['sll.pkttype'] == TRANS
            df = df[df['sll.pkttype'] == TRANS]
        elif direction == 'uplink':
            # condition1 = df['sll.pkttype'] == RECV
            df = df[df['sll.pkttype'] == RECV]
    ### TCP or UDP
    if protocol == 'udp':
        # condition2 = df['ip.proto'] == UDP
        df = df[df['ip.proto'] == UDP]
    elif protocol == 'tcp':
        # condition2 = df['ip.proto'] == TCP
        df = df[df['ip.proto'] == TCP]
    ### iPerf3 Payloads
    ### Original iPerf3
    # df = df[df['data.data'] != np.nan]
    # df = df[df['data.len'] != 0]
    # df = df[df['data.len'] % Payload.LENGTH == 0]
    ### Modified iPerf3
    if protocol == 'udp':
        # condition3 = df['udp.payload'].str.contains(Payload.TAG)
        df = df[df['udp.payload'].str.contains(Payload.TAG)]
    elif protocol == 'tcp':
        # condition3 = df['tcp.payload'].str.contains(Payload.TAG)
        df = df[df['tcp.payload'].str.contains(Payload.TAG)]
    # df = df[condition1 & condition2 & condition3]
    return df

def parse_packet_info(df, mode, fout):
    """
    Parse packet info.

    Args:
        df (pandas.Dataframe)
        mode (str): 'tx' or 'rx
    Returns:
        df (pandas.Dataframe)
    """
    ### Parse packet info | Stage 1
    # repackage: transport layer protocol may repackage multiple payload into 1 frame (capture),
    #            so data.len would be an integer multiple of customized Payload.LENTGH.
    # solution. => repkg_num

    ### Extract the features that we need
    df = df[['frame.time', 'frame.time_epoch', 'udp.length', 'data.len', '_ws.col.Protocol', 'ip.proto', 'ip.src', 'ip.dst', 'udp.payload']]
    # df = df[['frame.time', 'frame.time_epoch', 'tcp.len', 'data.len', '_ws.col.Protocol', ''ip.proto', ip.src', 'ip.dst', 'tcp.payload']]
    ### Reset index
    df = df.reset_index(drop=True)
    ### Add features
    df = pd.DataFrame(df, columns=df.columns.tolist()+['repackage.num', 'sequence.number', 'payload.time', 'payload.time_epoch'])
    df = df.reindex(['frame.time', 'frame.time_epoch', 'udp.length', 'data.len', 'repackage.num', 'sequence.number', 'payload.time', 'payload.time_epoch', '_ws.col.Protocol', 'ip.proto', 'ip.src', 'ip.dst', 'udp.payload'], axis=1)

    for i in tqdm(range(len(df))):
        repkg_num = int(df.loc[i, 'udp.length'] // Payload.LENGTH)
        _offset = [s * Payload.LENGTH * 2 for s in list(range(repkg_num))]  # 1-Byte == 2-hex-digits
        payload = df.loc[i, 'udp.payload']  # string-type
        # print(repkg_num)
        _temp = [[], [], []]  # [[seq,], [gen_time,], [gen_time_epoch,]]
        for ofs in _offset:
            try:
                datetimedec = int(payload[ofs + Payload.OFS_TIME[0] : ofs + Payload.OFS_TIME[1]], 16)
                microsec = int(payload[ofs + Payload.OFS_USEC[0] : ofs + Payload.OFS_USEC[1]], 16)
                seq = int(payload[ofs + Payload.OFS_SEQN[0] : ofs + Payload.OFS_SEQN[1]], 16)
            except:
                print(traceback.format_exc())
                # print(df.loc[i-1, 'frame.time'])
                # print(df.loc[i-1, 'udp.payload'])
                print(df.loc[i, 'frame.time'])
                print(payload)
                sys.exit(1)
            gen_time = str(to_utc8(datetimedec + microsec * 1e-6))
            # print("   ", seq)
            # print("   ", gen_time)
            _temp[0].append(str(seq))
            _temp[1].append(gen_time)
            _temp[2].append(str(datetimedec + microsec * 1e-6))
        df.loc[i, 'repackage.num'] = str(round(repkg_num))
        df.loc[i, 'sequence.number'] = '@'.join(_temp[0])
        df.loc[i, 'payload.time'] = '@'.join(_temp[1])
        df.loc[i, 'payload.time_epoch'] = '@'.join(_temp[2])
    
    df.rename(columns = {'frame.time':'Timestamp', 'frame.time_epoch':'Timestamp_epoch'}, inplace=True)
    # if mode == 'rx':
    #     df.rename(columns = {'frame.time':'arrival.time', 'frame.time_epoch':'arrival.time_epoch'}, inplace=True)
    # elif mode == 'tx':
    #     df.rename(columns = {'frame.time':'transmit.time', 'frame.time_epoch':'transmit.time_epoch'}, inplace=True)
    print("output >>>", fout)
    df.to_csv(fout, index=False)
    return df

def parse_brief_info(df, mode, fout):
    """
    Parse packet brief info.

    Args:
        df (pandas.Dataframe)
        mode (str): 'tx' or 'rx
    Returns:
        df (pandas.Dataframe)
    """
    ### Parse packet loss | Stage 2
    # duplicate packets: It was found that we may receive the same payload data (with the same generating time & sequence number) on different arrival time.
    #                    However, UDP should not do retransmission, so we only take the first arrival payload data into account.
    # solution. => seq_set()
    # !!! When running experiment, iPerf3 & tcpdump should always start / restart synchronously.

    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    # if mode == 'rx':
    #     df['arrival.time'] = pd.to_datetime(df['arrival.time'])
    # elif mode == 'tx':
    #     df['transmit.time'] = pd.to_datetime(df['transmit.time'])

    timestamp_list = []
    seq_set = set()
    for i in tqdm(range(len(df))):
        # ftime = df.loc[i, 'arrival.time'] if mode == 'rx' else df.loc[i, 'transmit.time']
        # ftime_epoch = df.loc[i, 'arrival.time_epoch'] if mode == 'rx' else df.loc[i, 'transmit.time_epoch']
        ftime = df.loc[i, 'Timestamp']
        ftime_epoch = df.loc[i, 'Timestamp_epoch']
        _seq = [int(s) for s in df.loc[i, 'sequence.number'].split('@')]
        _ptime = [str_to_datetime(s) for s in df.loc[i, 'payload.time'].split('@')]
        _ptime_epoch = [float(s) for s in df.loc[i, 'payload.time_epoch'].split('@')]
        for seq, ptime, ptime_epoch in zip(_seq, _ptime, _ptime_epoch):
            if seq not in seq_set:
                timestamp_list.append([seq, ftime, ftime_epoch, ptime, ptime_epoch])
                seq_set.add(seq)

    ### Consider there are out-of-order packets
    timestamp_list = sorted(timestamp_list, key = lambda v : v[0])

    ### Output the results
    print("output >>>", fout)
    with open(fout, "w", newline='') as fp:
        writer = csv.writer(fp)
        writer.writerow(['sequence.number', 'Timestamp', 'Timestamp_epoch', 'payload.time', 'payload.time_epoch'])
        # if mode == 'rx':
        #     writer.writerow(['sequence.number', 'arrival.time', 'arrival.time_epoch', 'payload.time', 'payload.time_epoch'])
        # elif mode == 'tx':
        #     writer.writerow(['sequence.number', 'transmit.time', 'transmit.time_epoch', 'payload.time', 'payload.time_epoch'])
        writer.writerows(timestamp_list)
    return df

### get latency needs to apply da-shen's method to synchronize the data, so get packet loss first.
def get_latency_jitter(rxdf, txdf, fout, mode):
    ### !!! Downlink: arrival time (client, rxdf.frame.time) | payload generating time (client, rxdf.payload.time) | transmitted time (server, txdf.frame.time)
    ### !!! Uplink:   arrival time (server, rxdf.frame.time) | payload generating time (server, rxdf.payload.time) | transmitted time (client, txdf.frame.time)
    rxdf['Timestamp'] = pd.to_datetime(rxdf['Timestamp'])
    rxdf['payload.time'] = pd.to_datetime(rxdf['payload.time'])
    # txdf['Timestamp'] = pd.to_datetime(txdf['Timestamp'])
    # txdf['payload.time'] = pd.to_datetime(txdf['payload.time'])

    ### calculate latency
    rxdf['latency'] = (rxdf['Timestamp'] - rxdf['payload.time']).dt.total_seconds().round(6)
    ### add transmitted timestamp
    # j = 0
    # N = len(rxdf)
    # rxdf = rxdf.reindex(rxdf.columns.tolist() + ['transmit.time', 'transmit.time_epoch'], axis=1)
    # for i in tqdm(range(len(txdf))):
    #     if txdf.loc[i, 'sequence.number'] == rxdf.loc[j, 'sequence.number']:
    #         rxdf.loc[j, 'transmit.time'] = txdf.loc[i, 'Timestamp']
    #         rxdf.loc[j, 'transmit.time_epoch'] = txdf.loc[i, 'Timestamp_epoch']
    #         j += 1
    #         if j == N:
    #             break
    rx_seq_arr = rxdf['sequence.number'].array
    tx_seq_arr = txdf['sequence.number'].array
    tx_ts_arr = txdf['Timestamp'].array
    tx_ts_epoch_arr = txdf['Timestamp_epoch'].array
    rx_tts_arr = []
    rx_tts_epoch_arr = []
    j = 0
    N = len(rx_seq_arr)
    for i in tqdm(range(len(tx_seq_arr))):
        # if txdf.loc[i, 'sequence.number'] == rxdf.loc[j, 'sequence.number']:
        if tx_seq_arr[i] == rx_seq_arr[j]:
            rx_tts_arr.append(tx_ts_arr[i])
            rx_tts_epoch_arr.append(tx_ts_epoch_arr[i])
            j += 1
            if j == N:
                break
    rxdf = rxdf.join(pd.DataFrame({'transmit.time' : rx_tts_arr, 'transmit.time_epoch' : rx_tts_epoch_arr}))
    rxdf.dropna(how='any', subset=['transmit.time', 'transmit.time_epoch'], axis=0, inplace=True)
    ### calculate jitter: average of latency difference between each packets
    jitter = 0
    rx_lat_arr = rxdf['latency'].array
    for i in range(len(rxdf)):
        if rx_lat_arr[i] < 0:
            print("******************************************************")
            # print("Latency should not be negative!!! Force to terminate.")
            print("Latency should not be negative!!!")
            if i > 0:
                print(rxdf[['sequence.number', 'Timestamp', 'latency']].iloc[i-1])
            print(rxdf[['sequence.number', 'Timestamp', 'latency']].iloc[i])
            print("******************************************************")
            sys.exit(1)
            # break
        if i == 0:
            continue
        # jitter = jitter + abs(rxdf.loc[i, 'latency'] - rxdf.loc[i-1, 'latency'])
        jitter = jitter + abs(rx_lat_arr[i] - rx_lat_arr[i-1])
    jitter = round(jitter / (len(rxdf) - 1), 6)

    if mode == 'ul':
        rxdf.rename(columns={'Timestamp' : 'arrival.time', 'Timestamp_epoch' : 'arrival.time_epoch',
                            'transmit.time' : 'Timestamp', 'transmit.time_epoch' : 'Timestamp_epoch'},
                            inplace=True)
        rxdf = rxdf.reindex("sequence.number,Timestamp,Timestamp_epoch,payload.time,payload.time_epoch,latency,arrival.time,arrival.time_epoch".split(','), axis=1)
    print("output >>>", fout)
    rxdf.to_csv(fout, index=False)

    if len(rxdf):
        return jitter, min(rxdf['latency']), max(rxdf['latency'])
    else:
        return 0, 0, 0

def get_loss(rxdf, txdf, fout1, fout2, mode):
    rxdf['Timestamp'] = pd.to_datetime(rxdf['Timestamp'])
    rxdf['payload.time'] = pd.to_datetime(rxdf['payload.time'])
    # txdf['Timestamp'] = pd.to_datetime(txdf['Timestamp'])
    # txdf['payload.time'] = pd.to_datetime(txdf['payload.time'])

    _eseq = 1  # next expected sequence number
    timestamp_list = list(map(list, zip(rxdf['sequence.number'].astype(int).array, rxdf['Timestamp_epoch'].astype(float).array)))
    timestamp_store = None
    loss_timestamp_list = []
    count = 0  # to count the total number of packet losses
    for i in tqdm(range(len(rxdf))):
        timestamp = timestamp_list[i]
        if timestamp[0] == _eseq:
            ### received packet's sequence number as expected
            pass
        else:
            ### packet losses occur
            ### 可處理連續掉 N 個封包的狀況
            ### timestamp_store: 前一刻收到的封包
            ### timestamp: 此時此刻收到的封包
            ### _eseq 為預期收到的封包 sequence number (前一刻收到的 seq number + 1)
            ### rxdf.loc[i, 'sequence.number'] 為此時此刻收到的封包 seq
            ### rxdf.loc[i, 'sequence.number']-pointer+2 == 遺漏的封包數+2 (頭+尾)，因此要去頭去尾才是實際遺漏的封包
            n = timestamp[0] - _eseq + 2
            if timestamp_store == None:
                ### if the first-N packets lost, we cannot predict the loss timestamp, so we only record their sequemce number.
                loss_linspace = np.linspace([0, timestamp[1] - (n-1) / PKT_RATE], timestamp, n)
            else:
                loss_linspace = np.linspace(timestamp_store, timestamp, n)
            
            loss_linspace = loss_linspace[1:-1]  # 去頭去尾
            for item in loss_linspace:
                count += 1
                loss_time = [round(item[0]), to_utc8(item[1]), item[1]]
                loss_timestamp_list.append(loss_time)
        # Update information
        timestamp_store = timestamp
        _eseq = timestamp[0] + 1
    
    ### add payload & transmitted timestamp
    tx_ts_arr = list(zip(txdf['sequence.number'].array, txdf['payload.time'].array, txdf['payload.time_epoch'].array, txdf['Timestamp'].array, txdf['Timestamp_epoch'].array))
    j = 0
    N = len(loss_timestamp_list)
    for i in tqdm(range(len(tx_ts_arr))):
        if N == 0:
            break
        if tx_ts_arr[i][0] == loss_timestamp_list[j][0]:
            loss_timestamp_list[j].append(tx_ts_arr[i][1])
            loss_timestamp_list[j].append(tx_ts_arr[i][2])
            loss_timestamp_list[j].append(tx_ts_arr[i][3])
            loss_timestamp_list[j].append(tx_ts_arr[i][4])
            j += 1
            if j == N:
                break
    ### 因為是由 Client 端主動開始和結束實驗，且程式邏輯為: 開 Tcpdump -> 開 iperf -> 關 Tcpdump -> 關 iperf
    ### 因此 Uplink TX 的 MAX_SEQ 會比 RX 小，Downlink TX 的 MAX_SEQ 會比 RX 大。
    loss_timestamp_list = [item for item in loss_timestamp_list if len(item) == 7]

    ### Output the results
    ### !!! Downlink: expected arrival time (client, rxdf.frame.time) | payload generating time (server, txdf.payload.time) | transmitted time      (server, txdf.frame.time)
    ### !!! Uplink:   transmitted time      (client, txdf.frame.time) | payload generating time (client, txdf.payload.time) | expected arrival time (server, rxdf.frame.time)
    if mode == 'ul':
        # print("Recombination!!")
        loss_timestamp_list = [[item[0], item[5], item[6], item[3], item[4], item[1], item[2]] for item in loss_timestamp_list]
    print("output >>>", fout1)
    with open(fout1, "w", newline='') as fp:
        writer = csv.writer(fp)
        if mode == 'dl':
            writer.writerow(['sequence.number', 'Timestamp', 'Timestamp_epoch', 'payload.time', 'payload.time_epoch', 'transmit.time', 'transmit.time_epoch'])
        elif mode == 'ul':
            writer.writerow(['sequence.number', 'Timestamp', 'Timestamp_epoch', 'payload.time', 'payload.time_epoch', 'expected_arrival.time', 'expected_arrival.time_epoch'])
        writer.writerows(loss_timestamp_list)
    return loss_timestamp_list

def get_statistics(loss_df, lat_df, fout1, fout2, mode):
    total_packet_sent = len(loss_df) + len(lat_df)
    total_loss = len(loss_df)
    loss_rate = len(loss_df) / (len(loss_df) + len(lat_df) + 1e-9) * 100  # ratio (%)
    if mode == 'dl':
        exp_time = round(lat_df['Timestamp_epoch'].iloc[-1] - lat_df['transmit.time_epoch'].iloc[0], 6) if total_packet_sent else 0
    elif mode == 'ul':
        exp_time = round(lat_df['arrival.time_epoch'].iloc[-1] - lat_df['Timestamp_epoch'].iloc[0], 6) if total_packet_sent else 0
    print("output >>>", fout1)
    with open(fout1, "w", newline='') as fp:
        writer = csv.writer(fp)
        writer.writerow(['total_packet_sent', 'total_packet_loss', 'packet_loss_rate(%)', 'experiment_time(sec)'])
        writer.writerow([total_packet_sent, total_loss, loss_rate, exp_time])
    
    _lat_df = lat_df[lat_df['latency'] > 100e-3]
    total_packet_recv = len(lat_df)
    total_excs_latency = len(_lat_df)
    excs_latency_rate = len(_lat_df) / (len(lat_df) + 1e-9) * 100  # ratio (%)
    print("output >>>", fout2)
    with open(fout2, "w", newline='') as fp:
        writer = csv.writer(fp)
        writer.writerow(['total_packet_recv', 'total_excessive_latency', 'excessive_latency_rate(%)', 'experiment_time(sec)'])
        writer.writerow([total_packet_recv, total_excs_latency, excs_latency_rate, exp_time])
    return (total_packet_sent, total_packet_recv, total_loss, loss_rate, total_excs_latency, excs_latency_rate, exp_time)


if __name__ == "__main__":
    t = TicToc()  # create instance of class
    t.tic()  # Start timer
    # --------------------- (3) decode a batch of files (User Settings) ---------------------
    # err_handles = []
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

        # # --------------------- Phase 1: Parse basic information --------------------- 
        # ##### Downlink
        # ### Read files: server_DL (Tx), client_DL (Rx)
        # print(_exp)
        # for j in range(_times):
        #     for i, dev in enumerate(devices):
        #         print(exp_dirs[i][j])
        #         dirpath = os.path.join(exp_dirs[i][j], "data")
        #         filenames = os.listdir(dirpath)
        #         for filename in filenames:
        #             if filename.startswith(("client_pcap_DL", "client_pcap_BL")) and filename.endswith(".csv"):
        #                 rxfile = filename
        #             if filename.startswith(("server_pcap_DL", "server_pcap_BL")) and filename.endswith(".csv"):
        #                 txfile = filename
        #         rxfin = os.path.join(dirpath, rxfile)
        #         txfin = os.path.join(dirpath, txfile)

        #         makedir(os.path.join(dirpath, "..", "analysis"))

        #         t1 = TicToc()  # create instance of class
        #         t1.tic()  # Start timer
        #         rxdf = pd.read_csv(rxfin, sep='@')
        #         ### Filtering
        #         print(">>>>>", rxfin)
        #         rxdf = filter(rxdf, 'client', 'downlink', 'udp')
        #         ### Parse packet payload information
        #         rxfout = os.path.join(dirpath, "..", "analysis", "clt_dwnlnk_udp_packet_info.csv")
        #         rxdf = parse_packet_info(rxdf, 'rx', rxfout)
        #         ### Parse packet brief information
        #         rxfout = os.path.join(dirpath, "..", "analysis", "clt_dwnlnk_udp_packet_brief.csv")
        #         parse_brief_info(rxdf, 'rx', rxfout)
        #         t1.toc()

        #         t1 = TicToc()  # create instance of class
        #         t1.tic()  # Start timer
        #         txdf = pd.read_csv(txfin, sep='@')
        #         ### Filtering
        #         print(">>>>>", txfin)
        #         txdf = filter(txdf, 'server', 'downlink', 'udp')
        #         ### Parse packet payload information
        #         txfout = os.path.join(dirpath, "..", "analysis", "srv_dwnlnk_udp_packet_info.csv")
        #         txdf = parse_packet_info(txdf, 'tx', txfout)
        #         ### Parse packet brief information
        #         txfout = os.path.join(dirpath, "..", "analysis", "srv_dwnlnk_udp_packet_brief.csv")
        #         parse_brief_info(txdf, 'tx', txfout)
        #         t1.toc()

        # ##### Uplink
        # ### Read files: client_UL (Tx), server_UL (Rx)
        # print(_exp)
        # for j in range(_times):
        #     for i, dev in enumerate(devices):
        #         print(exp_dirs[i][j])
        #         dirpath = os.path.join(exp_dirs[i][j], "data")
        #         filenames = os.listdir(dirpath)
        #         for filename in filenames:
        #             if filename.startswith(("server_pcap_UL", "server_pcap_BL")) and filename.endswith(".csv"):
        #                 rxfile = filename
        #             if filename.startswith(("client_pcap_UL", "client_pcap_BL")) and filename.endswith(".csv"):
        #                 txfile = filename
        #         rxfin = os.path.join(dirpath, rxfile)
        #         txfin = os.path.join(dirpath, txfile)

        #         makedir(os.path.join(dirpath, "..", "analysis"))

        #         t1 = TicToc()  # create instance of class
        #         t1.tic()  # Start timer
        #         rxdf = pd.read_csv(rxfin, sep='@')
        #         ### Filtering
        #         print(">>>>>", rxfin)
        #         rxdf = filter(rxdf, 'server', 'uplink', 'udp')
        #         ### Parse packet payload information
        #         rxfout = os.path.join(dirpath, "..", "analysis", "srv_uplnk_udp_packet_info.csv")
        #         rxdf = parse_packet_info(rxdf, 'rx', rxfout)
        #         ### Parse packet brief information
        #         rxfout = os.path.join(dirpath, "..", "analysis", "srv_uplnk_udp_packet_brief.csv")
        #         parse_brief_info(rxdf, 'rx', rxfout)
        #         t1.toc()

        #         t1 = TicToc()  # create instance of class
        #         t1.tic()  # Start timer
        #         txdf = pd.read_csv(txfin, sep='@')
        #         ### Filtering
        #         print(">>>>>", txfin)
        #         txdf = filter(txdf, 'client', 'uplink', 'udp')
        #         ### Parse packet payload information
        #         txfout = os.path.join(dirpath, "..", "analysis", "clt_uplnk_udp_packet_info.csv")
        #         txdf = parse_packet_info(txdf, 'tx', txfout)
        #         ### Parse packet brief information
        #         txfout = os.path.join(dirpath, "..", "analysis", "clt_uplnk_udp_packet_brief.csv")
        #         parse_brief_info(txdf, 'tx', txfout)
        #         t1.toc()
        
        # --------------------- Phase 2: Parse packet loss & latency --------------------- 
        ### Read files
        print(_exp)
        for j in range(_times):
            for i, dev in enumerate(devices):
                print(exp_dirs[i][j])
                dirpath = os.path.join(exp_dirs[i][j], "analysis")
                
                t1 = TicToc()  # create instance of class
                t1.tic()  # Start timer
                txdl_df = pd.read_csv(os.path.join(dirpath, "srv_dwnlnk_udp_packet_brief.csv"))
                rxdl_df = pd.read_csv(os.path.join(dirpath, "clt_dwnlnk_udp_packet_brief.csv"))
                txul_df = pd.read_csv(os.path.join(dirpath, "clt_uplnk_udp_packet_brief.csv"))
                rxul_df = pd.read_csv(os.path.join(dirpath, "srv_uplnk_udp_packet_brief.csv"))
                txdl_df['Timestamp'] = pd.to_datetime(txdl_df['Timestamp'])  # transmitted time from server
                rxdl_df['Timestamp'] = pd.to_datetime(rxdl_df['Timestamp'])  # arrival time to client
                txul_df['Timestamp'] = pd.to_datetime(txul_df['Timestamp'])  # transmitted time from client
                rxul_df['Timestamp'] = pd.to_datetime(rxul_df['Timestamp'])  # arrival time to server
                txdl_df['payload.time'] = pd.to_datetime(txdl_df['payload.time'])
                rxdl_df['payload.time'] = pd.to_datetime(rxdl_df['payload.time'])
                txul_df['payload.time'] = pd.to_datetime(txul_df['payload.time'])
                rxul_df['payload.time'] = pd.to_datetime(rxul_df['payload.time'])
                
                timedelta, epoch_delta = calc_delta(txdl_df, rxdl_df, txul_df, rxul_df)

                ### Downlink handle
                rxdl_df['Timestamp'] = rxdl_df['Timestamp'] + timedelta[0]
                rxdl_df['Timestamp_epoch'] = rxdl_df['Timestamp_epoch'] + epoch_delta[0]
                ### Uplink handle
                txul_df['Timestamp'] = txul_df['Timestamp'] + timedelta[1]
                txul_df['Timestamp_epoch'] = txul_df['Timestamp_epoch'] + epoch_delta[1]
                txul_df['payload.time'] = txul_df['payload.time'] + timedelta[1]
                txul_df['payload.time_epoch'] = txul_df['payload.time_epoch'] + epoch_delta[1]
                rxul_df['payload.time'] = rxul_df['payload.time'] + timedelta[1]
                rxul_df['payload.time_epoch'] = rxul_df['payload.time_epoch'] + epoch_delta[1]
                t1.toc()
                print()
                
                _epoch_delta = round((epoch_delta[0] + epoch_delta[1]) / 2, 6)
                if _epoch_delta >= 0:
                    print("Client time is behind by {} ms".format(abs(_epoch_delta * 1000)))
                else:
                    print("Client time is ahead by {} ms".format(abs(_epoch_delta * 1000)))
                
                fout1_dl = os.path.join(dirpath, "dwnlnk_udp_loss_timestamp.csv")
                fout2_dl = os.path.join(dirpath, "dwnlnk_udp_loss_statistics.csv")
                fout3_dl = os.path.join(dirpath, "dwnlnk_udp_latency.csv")
                fout1_ul = os.path.join(dirpath, "uplnk_udp_loss_timestamp.csv")
                fout2_ul = os.path.join(dirpath, "uplnk_udp_loss_statistics.csv")
                fout3_ul = os.path.join(dirpath, "uplnk_udp_latency.csv")
                
                jitter, min_latency, max_latency = get_latency_jitter(rxdl_df, txdl_df, fout3_dl, 'dl')
                loss_timestamp = get_loss(rxdl_df, txdl_df, fout1_dl, fout2_dl, 'dl')
                # loss_timestamp, loss_statistics, err_handle = get_loss(rxdl_df, txdl_df, fout1_dl, fout2_dl)
                # err_handles.append((os.path.join(dirpath, "clt_dwnlnk_udp_packet_brief.csv"), '-', err_handle))

                dl_loss_df = pd.read_csv(os.path.join(dirpath, "dwnlnk_udp_loss_timestamp.csv"))
                dl_lat_df = pd.read_csv(os.path.join(dirpath, "dwnlnk_udp_latency.csv"))
                fout1_dl = os.path.join(dirpath, "dwnlnk_udp_loss_statistics.csv")
                fout2_dl = os.path.join(dirpath, "dwnlnk_udp_ex-latency_statistics.csv")
                _stats = get_statistics(dl_loss_df, dl_lat_df, fout1_dl, fout2_dl, 'dl')

                print("------------------------------------------")
                print("jitter:              ", jitter)
                print("min latency:         ", min_latency)
                print("max latency:         ", max_latency)
                print("total_packet_sent:   ", _stats[0])
                print("total_packet_recv:   ", _stats[1])
                print("total_packet_loss:   ", _stats[2])
                print("packet_loss_rate(%): ", _stats[3])
                print("total_excs_latency:  ", _stats[4])
                print("excs_latency_rate(%):", _stats[5])
                print("experiment_time(sec):", _stats[6])
                print("------------------------------------------")
                print()
                
                jitter, min_latency, max_latency = get_latency_jitter(rxul_df, txul_df, fout3_ul, 'ul')
                loss_timestamp = get_loss(rxul_df, txul_df, fout1_ul, fout2_ul, 'ul')
                # loss_timestamp, loss_statistics, err_handle = get_loss(rxul_df, txul_df, fout1_ul, fout2_ul)
                # err_handles.append((os.path.join(dirpath, "srv_uplnk_udp_packet_brief.csv"), '-', err_handle))

                ul_loss_df = pd.read_csv(os.path.join(dirpath, "uplnk_udp_loss_timestamp.csv"))
                ul_lat_df = pd.read_csv(os.path.join(dirpath, "uplnk_udp_latency.csv"))
                fout1_ul = os.path.join(dirpath, "uplnk_udp_loss_statistics.csv")
                fout2_ul = os.path.join(dirpath, "uplnk_udp_ex-latency_statistics.csv")
                _stats = get_statistics(ul_loss_df, ul_lat_df, fout1_ul, fout2_ul, 'ul')

                print("------------------------------------------")
                print("jitter:              ", jitter)
                print("min latency:         ", min_latency)
                print("max latency:         ", max_latency)
                print("total_packet_sent:   ", _stats[0])
                print("total_packet_recv:   ", _stats[1])
                print("total_packet_loss:   ", _stats[2])
                print("packet_loss_rate(%): ", _stats[3])
                print("total_excs_latency:  ", _stats[4])
                print("excs_latency_rate(%):", _stats[5])
                print("experiment_time(sec):", _stats[6])
                print("------------------------------------------")
                print()
    # ### Check errors
    # flag = False
    # for err_handle in err_handles:
    #     flag = error_handling(err_handle)
    # if not flag:
    #     print("**************************************************")
    #     print("No error occurs!!")
    #     print("**************************************************")
    t.toc()  # Time elapsed since t.tic()
