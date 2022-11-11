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

PORT = args.port1           # UL

thread_stop = False
exit_program = False
length_packet = 362
pcap_path = "."

now = dt.datetime.today()
n = [str(x) for x in[ now.year, now.month, now.day, now.hour, now.minute, now.second]]
for i in range(len(n)-3, len(n)):
    if len(n[i]) < 2:
        n[i] = '0' + n[i]
n = '-'.join(n)

pcapfile1 = "%s/DL_%s_%s.pcap"%(pcap_path, PORT, n)
tcpproc1 =  subprocess.Popen(["tcpdump -i any port %s -w %s &"%(PORT,  pcapfile1)], shell=True, preexec_fn=os.setsid)
socket_proc =  subprocess.Popen(["iperf3 -s -B 0.0.0.0 -p %d"%(PORT)], shell=True, preexec_fn=os.setsid)
time.sleep(1)

ss_dir = "ss"

def get_ss(port, type):
    global thread_stop
    global n
    f = ""

    if type == 't':
        f = open(os.path.join(ss_dir, "ss_server_DL_" + str(port) + '_' + n)+'.csv', 'a+')
    elif type == 'r':
        f = open(os.path.join(ss_dir, "ss_server_UL_" + str(port) + '_' + n)+'.csv', 'a+')
    print(f)
    while not thread_stop:
        proc = subprocess.Popen(["ss -ai src :%d"%(port)], stdout=subprocess.PIPE, shell=True)

        text = proc.communicate()[0].decode()
        lines = text.split('\n')

        for line in lines:
            if "bytes_sent" in line:
                l = line.strip()
                f.write(",".join([str(dt.datetime.now())]+ re.split("[: \n\t]", l))+'\n')
                break
        time.sleep(1)
    f.close()


get_ss_thread = threading.Thread(target = get_ss, args = (PORT, 't'))
get_ss_thread.start()


while True:


    try:
        time.sleep(1)
    except KeyboardInterrupt:
        os.killpg(os.getpgid(socket_proc.pid), signal.SIGTERM)
        os.killpg(os.getpgid(tcpproc1.pid), signal.SIGTERM)
        break
    except Exception as e:
        print("error", e)

thread_stop = True
os.system("killall -9 iperf3")
os.killpg(os.getpgid(tcpproc1.pid), signal.SIGTERM)
