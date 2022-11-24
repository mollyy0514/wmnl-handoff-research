#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
    
    Author: Jing-You, Yan

    This script will create two sockets, UL and DL.
    You could change the PARAMETERS below.

    Run:
        $ python3 client.py -p Port -H server_ip_address
    ex:
        $ python3 client.py -p 3270 -d 140.112.20.183

"""



import socket
import time
import threading
import datetime as dt
import select
import sys
import os
import queue
import argparse
import subprocess
import re
import numpy as np
import signal

parser = argparse.ArgumentParser()
parser.add_argument("-p", "--port", type=int,
                    help="port to bind", default=3250)
parser.add_argument("-H", "--HOST", type=str,
                    help="server ip address", default="140.112.20.183")
                    #help="server ip address", default="210.65.88.213")
args = parser.parse_args()

HOST = args.HOST
port = args.port



num_ports = 1
UL_ports = np.arange(port, port+2*num_ports, 2)
DL_ports = np.arange(port+1, port+1+2*num_ports, 2)
TCP_CONGESTION = 13

thread_stop = False
exit_program = False


## PARAMETERS ###################
length_packet = 400
bandwidth = 5000*1024 # unit kbps
total_time = 3600
pcap_path = "pcapdir"
exitprogram = False
cong = 'reno'.encode()
ss_dir = "ss"
#################################

expected_packet_per_sec = bandwidth / (length_packet << 3)
sleeptime = 1.0 / expected_packet_per_sec
prev_sleeptime = sleeptime


def get_ss(port, type):
    now = dt.datetime.today()
    n = '-'.join([str(x) for x in[ now.year, now.month, now.day, now.hour, now.minute, now.second]])
    f = ""
    if type == 't':
        f = open(os.path.join(ss_dir, "ss_client_UL_" + str(port) + '_' + n)+'.csv', 'a+')
    elif type == 'r':
        f = open(os.path.join(ss_dir, "ss_client_DL_" + str(port) + '_' + n)+'.csv', 'a+')
    global thread_stop
    while not thread_stop:
        proc = subprocess.Popen(["ss -ai dst :%d"%(port)], stdout=subprocess.PIPE, shell=True)

        text = proc.communicate()[0].decode()
        lines = text.split('\n')

        for line in lines:
            if "bytes_sent" in line:
                l = line.strip()
                f.write(",".join([str(dt.datetime.now())]+ re.split("[: \n\t]", l))+'\n')
                break
        time.sleep(1)
    f.close()

def connection_setup(host, port, result):
    s_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s_tcp.setsockopt(socket.IPPROTO_TCP, TCP_CONGESTION, cong)
    s_tcp.settimeout(10)
    s_tcp.connect((host, port))

    while True:
        print("%d wait for starting..."%(port))
        try:
            indata = s_tcp.recv(65535)
            if indata == b'START':
                print("START")
                break
            else:
                print("WTF", indata)
                break
        except Exception as inst:
            print("Error: ", inst)

    result[0] = s_tcp

def transmision(stcp_list):
    print("start transmision", stcp_list)
    i = 0
    prev_transmit = 0
    ok = (1).to_bytes(1, 'big')
    start_time = time.time()
    count = 1
    sleeptime = 1.0 / expected_packet_per_sec
    prev_sleeptime = sleeptime
    global thread_stop
    while time.time() - start_time < total_time and not thread_stop:
        try:
            t = time.time()
            t = int(t*1000).to_bytes(8, 'big')
            z = i.to_bytes(4, 'big')
            redundant = os.urandom(length_packet-12-1)
            outdata = t + z + ok +redundant
            for j in range(len(stcp_list)):
                stcp_list[j].sendall(outdata)
            i += 1
            time.sleep(sleeptime)
            if time.time()-start_time > count:
                transmit_bytes = (i-prev_transmit) * length_packet
                if transmit_bytes <= 1024*1024:
                    print("[%d-%d]"%(count-1, count), "%g kbps"%(transmit_bytes/1024*8))
                else:
                    print("[%d-%d]"%(count-1, count), "%g Mbps"%(transmit_bytes/1024/1024*8))
                count += 1
                sleeptime = (prev_sleeptime / expected_packet_per_sec * (i-prev_transmit) + sleeptime) / 2
                prev_transmit = i
                prev_sleeptime = sleeptime
        except:
            break
    thread_stop = True
    print("---transmision timeout---")
    print("transmit", i, "packets")


def receive(s_tcp, port):
    s_tcp.settimeout(10)
    print("wait for indata...")
    start_time = time.time()
    count = 1
    capture_bytes = 0
    global thread_stop
    global buffer
    buffer = queue.Queue()
    while not thread_stop:
        try:
            indata = s_tcp.recv(65535)
            capture_bytes += len(indata)
            if time.time()-start_time > count:
                if capture_bytes <= 1024*1024:
                    print(port, "[%d-%d]"%(count-1, count), "%g kbps"%(capture_bytes/1024*8))
                else:
                    print(port, "[%d-%d]"%(count-1, count), "%gMbps" %(capture_bytes/1024/1024*8))
                count += 1
                capture_bytes = 0
        except Exception as inst:
            print("Error: ", inst)
            thread_stop = True
    thread_stop = True
    if capture_bytes <= 1024*1024:
        print(port, "[%d-%d]"%(count-1, count), "%g kbps"%(capture_bytes/1024*8))
    else:
        print(port, "[%d-%d]"%(count-1, count), "%gMbps" %(capture_bytes/1024/1024*8))
    print("---Experiment Complete---")
    print("STOP receiving")


if not os.path.exists(pcap_path):
    os.system("mkdir %s"%(pcap_path))
if not os.path.exists(ss_dir):
    os.system("mkdir %s"%(ss_dir))


while not exitprogram:

    try:
        x = input("Press Enter to start\n")
        if x == "EXIT":
            break
        now = dt.datetime.today()

        n = [str(x) for x in[ now.year, now.month, now.day, now.hour, now.minute, now.second]]
        for i in range(len(n)-3, len(n)):
            if len(n[i]) < 2:
                n[i] = '0' + n[i]
        n = '-'.join(n)

        UL_pcapfiles = []
        DL_pcapfiles = []
        tcpdump_UL_proc = []
        tcpdump_DL_proc = []
        get_ss_thread = []

        for p in UL_ports:
            UL_pcapfiles.append("%s/client_UL_%s_%s.pcap"%(pcap_path, p, n))
        for p in DL_ports:
            DL_pcapfiles.append("%s/client_DL_%s_%s.pcap"%(pcap_path, p, n))

        for p, pcapfile in zip(UL_ports, UL_pcapfiles):
            tcpdump_UL_proc.append(subprocess.Popen(["tcpdump -i any port %s -w %s &"%(p,pcapfile)], shell=True, preexec_fn=os.setsid))
            get_ss_thread.append(threading.Thread(target = get_ss, args = (p, 't')))

        for p, pcapfile in zip(DL_ports, DL_pcapfiles):
            tcpdump_DL_proc.append(subprocess.Popen(["tcpdump -i any port %s -w %s &"%(p,pcapfile)], shell=True, preexec_fn=os.setsid))
            get_ss_thread.append(threading.Thread(target = get_ss, args = (p, 'r')))

        thread_list = []
        UL_result_list = []
        DL_result_list = []

        UL_tcp_list = [None] * num_ports
        DL_tcp_list = [None] * num_ports

        for i in range(num_ports):
            UL_result_list.append([None])
            DL_result_list.append([None])

        for i in range(len(UL_ports)):
            thread_list.append(threading.Thread(target = connection_setup, args = (HOST, UL_ports[i], UL_result_list[i])))

        for i in range(len(DL_ports)):
            thread_list.append(threading.Thread(target = connection_setup, args = (HOST, DL_ports[i], DL_result_list[i])))
        
        for i in range(len(thread_list)):
            thread_list[i].start()

        for i in range(len(thread_list)):
            thread_list[i].join()

        for i in range(num_ports):
            UL_tcp_list[i] = UL_result_list[i][0]
            DL_tcp_list[i] = DL_result_list[i][0]

        print("UL_tcp_list", UL_tcp_list)
        print("DL_tcp_list", DL_tcp_list)

        for i in range(num_ports):
            assert(UL_tcp_list[i] != None)
            assert(DL_tcp_list[i] != None)

    except Exception as inst:
        print("Error: ", inst)
        for i in range(len(UL_tcp_list)):
            os.killpg(os.getpgid(tcpdump_UL_proc[i].pid), signal.SIGTERM)
        for i in range(len(DL_tcp_list)):
            os.killpg(os.getpgid(tcpdump_DL_proc[i].pid), signal.SIGTERM)
        continue
    thread_stop = False

    thread_stop = False
    transmision_thread = threading.Thread(target = transmision, args = (UL_tcp_list, ))
    recive_thread_list = []
    for i in range(num_ports):
        recive_thread_list.append(threading.Thread(target = receive, args = (DL_tcp_list[i], DL_ports[i])))



    try:
        transmision_thread.start()
        for i in range(len(recive_thread_list)):
            recive_thread_list[i].start()
        for i in range(len(get_ss_thread)):
            get_ss_thread[i].start()
        transmision_thread.join()
        for i in range(len(recive_thread_list)):
            recive_thread_list[i].join()




        while transmision_thread.is_alive():
            x = input("Enter STOP to Stop\n")
            if x == "STOP":
                thread_stop = True
                break
            elif x == "EXIT":
                thread_stop = True
                exitprogram = True
        thread_stop = True


    except Exception as inst:
        print("Error: ", inst)
    except KeyboardInterrupt:
        print("finish")

    finally:
        thread_stop = True
        for i in range(num_ports):
            UL_tcp_list[i].close()
            DL_tcp_list[i].close()
        for i in range(len(UL_tcp_list)):
            os.killpg(os.getpgid(tcpdump_UL_proc[i].pid), signal.SIGTERM)
        for i in range(len(DL_tcp_list)):
            os.killpg(os.getpgid(tcpdump_DL_proc[i].pid), signal.SIGTERM)
