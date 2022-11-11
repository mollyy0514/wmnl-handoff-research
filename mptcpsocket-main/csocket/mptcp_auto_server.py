#!/usr/bin/env python3

import socket
import time
import threading
import os
import datetime as dt
import argparse
import subprocess
import re
import signal
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("-p1", "--port1", type=int,
                    help="port to bind", default=3270)
args = parser.parse_args()

IP_MTU_DISCOVER   = 10
IP_PMTUDISC_DONT  =  0  # Never send DF frames.
IP_PMTUDISC_WANT  =  1  # Use per route hints.
IP_PMTUDISC_DO    =  2  # Always DF.
IP_PMTUDISC_PROBE =  3  # Ignore dst pmtu.
TCP_CONGESTION = 13


HOST = '192.168.1.248'
PORT = args.port1           # UL

thread_stop = False
exit_program = False
length_packet = 362
bandwidth = 289.6*1000*10
total_time = 3600
cong_algorithm = 'cubic'
expected_packet_per_sec = bandwidth / (length_packet << 3)
sleeptime = 1.0 / expected_packet_per_sec
prev_sleeptime = sleeptime
pcap_path = "/home/wmnlab/D/pcap_data"
ss_dir = "/home/wmnlab/D/ss"
hostname = str(PORT) + ":"

cong = 'bbr'.encode()
exit_program = False

now = dt.datetime.today()
n = '-'.join([str(x) for x in[ now.year, now.month, now.day, now.hour, now.minute, now.second]])
pcapfile1 = "%s/UL_%s_%s.pcap"%(pcap_path, PORT, n)
filename = "s_port_%s_running.tmp"%(PORT)
os.system("echo \"idle\" > %s"%(filename))
tcpproc1 =  subprocess.Popen(["sudo tcpdump -i any port %s -w %s &"%(PORT,  pcapfile1)], shell=True, preexec_fn=os.setsid)
socket_proc =  subprocess.Popen(["./server.o %s"%(PORT)], shell=True)

while True:
    try:
        time.sleep(1)
        f = open(filename, 'r')
        l = f.readline()
        f.close()
        if "FINISH" in l:
            pid = l.split(" ")[1] # FINISH "PID"
            os.system("sudo kill -9 " + pid)
            
            os.killpg(os.getpgid(tcpproc1.pid), signal.SIGTERM)
            break
        elif "FAIL" in l:
            print("FAIL")
            pid = l.split(" ")[1] # FINISH "PID"
            os.system("sudo kill -9 " + pid)
            os.killpg(os.getpgid(tcpproc1.pid), signal.SIGTERM)
            break

    except KeyboardInterrupt:
        pid = l.split(" ")[1] # FINISH "PID"
        os.system("sudo kill -9 " + pid)
        os.killpg(os.getpgid(socket_proc.pid), signal.SIGTERM)
        os.killpg(os.getpgid(tcpproc1.pid), signal.SIGTERM)
        exit_program = True
        break
    except Exception as e:
        print("error", e)
        break

os.system("sudo killall -9 " + "server.o")
os.killpg(os.getpgid(tcpproc1.pid), signal.SIGTERM)