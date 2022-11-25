#!/usr/bin/env python3

# Command Usage:
# pip3 install adbutils
# ./auto_monitor_modem.py -d qc00 qc01

from adbutils import adb
import os
import sys
import time
import subprocess
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--devices", type=str, nargs='+',  # input list of devices sep by 'space'
                    help="list of devices", default=["unam"])
args = parser.parse_args()

device_to_serial = {
    "sm00":"R5CRA1ET5KB",
    "sm01":"R5CRA1D2MRJ",
    "sm02":"R5CRA1GCHFV",
    "sm03":"R5CRA1JYYQJ",
    "sm04":"R5CRA1EV0XH",
    "sm05":"R5CRA1GBLAZ",
    "sm06":"R5CRA1ESYWM",
    "sm07":"R5CRA1ET22M",
    "sm08":"R5CRA2EGJ5X",
    "xm00":"73e11a9f",
    "xm01":"491d5141",
    "xm02":"790fc81d",
    "xm03":"e2df293a",
    "xm04":"28636990",
    "xm05":"f8fe6582",
    "xm06":"d74749ee",
    "xm07":"10599c8d",
    "xm08":"57f67f91",
    "xm09":"232145e8",
    "xm10":"70e87dd6",
    "xm11":"df7aeaf8",
    "xm12":"e8c1eff5",
    "xm13":"ec32dc1e",
    "xm14":"2aad1ac6",
    "xm15":"64545f94",
    "xm16":"613a273a",
    "xm17":"fe3df56f",
    "qc00":"76857c8" ,
    "qc01":"bc4587d" ,
    "qc02":"5881b62f",
    "qc03":"32b2bdb2",
}

os.system("echo wmnlab | sudo -S su")

devices = sorted(os.listdir("/sys/class/net/"))
devices = [dev for dev in devices if dev.startswith('qc')]

# for i, dev in enumerate(args.devices):
for i, dev in enumerate(devices):
    print("{} - {} {}".format(i+1, device_to_serial[dev], dev))
print("-----------------------------------")

# # run iperf-client: fail to run via through this script on Android system
# for device, info in zip(devices, devices_info):
#     # print(info[2], device.shell("su"))
#     print(info[2], device.shell("su -c 'python3 /sdcard/wmnl-handoff-research/iperf-script/iperf_client_single.py -d {}'".format(info[2])))

# run mobileinsight
run_list = []
# for i, dev in enumerate(args.devices):
for i, dev in enumerate(devices):
    run_store = subprocess.Popen("sudo python3 monitor.py -d {} -b 9600".format(dev), shell=True, preexec_fn=os.setpgrp)
    run_list.append(run_store)
    # os.system("sudo python3 monitor-example.py -d {} -b 9600 &".format(dev))

for item in run_list:
    print(item.pid)
    
# kill python3 session if capture KeyboardInterrup
while True:
    try:
        time.sleep(1)  # detect every second
    except KeyboardInterrupt:
        # for run_item in run_list:
        #     print(run_item, ", PID: ", run_item.pid)
        #     os.system("sudo kill -9 {}".format(run_item.pid))
        # os.system("sudo pkill python3")
        os.system("ps -ef | grep python3 > ps_tmp.txt")
        with open('ps_list.txt', 'r') as fp:
            lines = fp.readlines()
        infos = [[] for i in range(len(lines))]
        for i, line in enumerate(lines):
            infos[i] = [s for s in line[:52].split(' ') if s]
            infos[i].append(line[52:-1])
        kill_list = []
        for info in infos:
            if info[7].startswith("python3 monitor.py"):
                kill_list.append(info[1])
        for info in infos:
            if info[7].startswith("python3 ./auto_monitor_modem.py"):
                kill_list.append(info[1])
        for pid in kill_list:
            os.system("sudo kill -9 {}".format(pid))
        os.system("sudo rm ps_list.txt")
        break
    except Exception as e:
        print("error", e)
