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
                    help="port to bind", default=3271)
args = parser.parse_args()

HOST = '192.168.1.248'
PORT = args.port1           # UL

thread_stop = False
exit_program = False
length_packet = 362
bandwidth = 40000 # kbytes / sec
total_time = 3600
cong_algorithm = 'cubic'
expected_packet_per_sec = bandwidth / (length_packet << 3)
sleeptime = 1.0 / expected_packet_per_sec
prev_sleeptime = sleeptime
pcap_path = "/home/wmnlab/D/pcap_data"
ss_dir = "/home/wmnlab/D/ss"
hostname = str(PORT) + ":"

cong = 'reno'.encode()

now = dt.datetime.today()
n = '-'.join([str(x) for x in[ now.year, now.month, now.day, now.hour, now.minute, now.second]])

pcapfile1 = "%s/DL_%s_%s.pcap"%(pcap_path, PORT, n)
filename = "sr_port_%s_running.tmp"%(PORT)
os.system("echo \"idle\" > %s"%(filename))
tcpproc1 =  subprocess.Popen(["tcpdump -i any port %s -w %s &"%(PORT,  pcapfile1)], shell=True, preexec_fn=os.setsid)
socket_proc =  subprocess.Popen(["./server_r.o %s %s %s&"%(PORT, bandwidth, length_packet)], shell=True, preexec_fn=os.setsid)
print(socket_proc.pid)
time.sleep(1)

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
        os.killpg(os.getpgid(socket_proc.pid), signal.SIGTERM)
        os.killpg(os.getpgid(tcpproc1.pid), signal.SIGTERM)
        break
    except Exception as e:
        print("error", e)


os.system("killall -9 server_r.o")
subprocess.Popen(["rm %s"%(filename)], shell=True)
os.killpg(os.getpgid(tcpproc1.pid), signal.SIGTERM)
