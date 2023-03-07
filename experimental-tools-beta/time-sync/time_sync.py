#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
pdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))  # for py-script
sys.path.insert(1, pdir)

import socket
import time
import csv
import json
import datetime as dt
from myutils import makedir

HOST = '140.112.20.183'
PORT = 3299

def clock_diff(device):
    server = []
    client = []
    with open(f"sync_client_{device}.csv", newline='') as f:
        reader = csv.reader(f)
        client = list(reader)
    with open(f"sync_server_{device}.csv", newline='') as f:
        reader = csv.reader(f)
        server = list(reader)

    diff = 0.0
    cnt = 0
    for i in range(len(client)):
        RTT = float(client[i][2]) - float(client[i][1])
        if(RTT > 0.1):
            continue
        cen_client = (float(client[i][2]) + float(client[i][1]))/2
        cen_server = (float(server[i][2]) + float(server[i][1]))/2
        diff += cen_server - cen_client
        cnt += 1
    diff /= cnt

    # diff > 0: client is behind server by abs(diff) seconds
    # diff < 0: client is ahead of server by abs(diff) seconds
    return diff

# client
if sys.argv[1] == '-c':
    with open('device.txt', 'r', encoding='utf-8') as f:
        device = f.readline().strip()
    
    now = dt.datetime.today()
    date = [str(x) for x in [now.year, now.month, now.day]]
    date = [x.zfill(2) for x in date]
    date = '-'.join(date)
    dirpath = f'./log/{date}'
    makedir(dirpath)
    
    server_addr = (HOST, PORT)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(3)
    num_packet_per_round = 100
    packet_interval = 0

    timestamp_client = []
    timestamp_server = []

    i = 0
    tmo_cnt = 0
    while i <= num_packet_per_round:
        time0 = time.time()
        outdata = str(i).zfill(3)
        s.sendto(outdata.encode(), server_addr)
        s.settimeout(3)
        try:
            indata, addr = s.recvfrom(1024)
            time1 = time.time()
            indata = indata.decode()
            tmo_cnt = 0
        except:
            print("timeout", outdata)
            tmo_cnt += 1
            if tmo_cnt == 3:
                break
            continue
        # print('recvfrom ' + str(addr) + ': ' + indata)
        print(outdata, time0, time1, "RTT =", (time1-time0)*1000, "ms")
        timestamp_client.append([outdata, time0, time1])
        timestamp_server.append(indata.split(' '))
        time.sleep(packet_interval)
        i += 1
    outdata = 'end'
    s.sendto(outdata.encode(), server_addr)

    with open('sync_client_'+device+'.csv', 'w') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerows(timestamp_client)
    with open('sync_server_'+device+'.csv', 'w') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerows(timestamp_server)
    
    current_time = dt.datetime.now()
    diff = clock_diff(device)
    print("device:", device)
    print(current_time, diff, "seconds")
    
    json_file = os.path.join(dirpath, f'time_sync_{device}.json')
    if os.path.isfile(json_file):
        with open(json_file, 'r') as f:
            json_object = json.load(f)
    else:
        json_object = {}
    json_object[str(current_time)] = diff
    with open(json_file, 'w') as f:
        json.dump(json_object, f)

# server
elif sys.argv[1] == '-s':
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('0.0.0.0', PORT))

    while True:
        print('server start at: %s:%s' % ('0.0.0.0', PORT))
        print('wait for connection...')

        while True:
            indata, addr = s.recvfrom(1024)
            time0 = time.time()
            indata = indata.decode()
            if indata == 'end':
                break
            print('recvfrom ' + str(addr) + ': ' + indata)
            
            time1 = time.time()
            outdata = f'{indata} {time0} {time1}'
            s.sendto(outdata.encode(), addr)
            print(indata, time0, time1)
