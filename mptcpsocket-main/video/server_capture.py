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


pcap_path = "."
PORT = 1935
hostname = str(PORT) + ":"

now = dt.datetime.today()
n = '-'.join([str(x) for x in[ now.year, now.month, now.day, now.hour, now.minute, now.second]])
pcapfile1 = "%s/server_%s_%s.pcap"%(pcap_path, PORT, n)
s = "tcpdump -i any port %s -w %s &"%(PORT,  pcapfile1)
print(s)
os.system(s)

while True:
    try:
        l = input()
        if l == "stop" or l == "STOP":
            break
    except KeyboardInterrupt:
        break
    except Exception as e:
        break

os.system("killall -9 tcpdump")
