#!/usr/bin/env python3

# Command Usage:
# pip3 install adbutils
# ./auto_monitor.py

from adbutils import adb
import os
import sys
import time
import subprocess

serial_to_device = {
    "R5CRA1ET5KB":"sm00",
    "R5CRA1D2MRJ":"sm01",
    "R5CRA1GCHFV":"sm02",
    "R5CRA1JYYQJ":"sm03",
    "R5CRA1EV0XH":"sm04",
    "R5CRA1GBLAZ":"sm05",
    "R5CRA1ESYWM":"sm06",
    "R5CRA1ET22M":"sm07",
    "R5CRA2EGJ5X":"sm08",
    "73e11a9f":"xm00",
    "491d5141":"xm01",
    "790fc81d":"xm02",
    "e2df293a":"xm03",
    "28636990":"xm04",
    "f8fe6582":"xm05",
    "d74749ee":"xm06",
    "10599c8d":"xm07",
    "57f67f91":"xm08",
    "232145e8":"xm09",
    "70e87dd6":"xm10",
    "df7aeaf8":"xm11",
    "e8c1eff5":"xm12",
    "ec32dc1e":"xm13",
    "2aad1ac6":"xm14",
    "64545f94":"xm15",
    "613a273a":"xm16",
    "fe3df56f":"xm17",
    "76857c8" :"qc00",
    "bc4587d" :"qc01",
    "5881b62f":"qc02",
    "32b2bdb2":"qc03",
}

device_to_serial = dict((v, k) for k, v in serial_to_device.items())

os.system("echo wmnlab | sudo -S su")

### Check Mobile
mobile_info = []
for i, info in enumerate(adb.list()):
    try:
        if info.state == "device":
            # <serial> <device|offline> <device name>
            mobile_info.append((info.serial, info.state, serial_to_device[info.serial]))
        else:
            print("Unauthorized device {}: {} {}".format(serial_to_device[info.serial], info.serial, info.state))
    except:
        print("Unknown device: {} {}".format(info.serial, info.state))

mobile_info = sorted(mobile_info, key=lambda v:v[2])

adb_handles = []
# print mobile info
for i, info in enumerate(mobile_info):
    adb_handles.append(adb.device(info[0]))
    print("{} - {} {} {}".format(i+1, info[0], info[1], info[2]))
# check unauthorized mobile
for info in adb.list():
    if info.state == "unauthorized":
        sys.exit(1)
# getprop
for device, info in zip(adb_handles, mobile_info):
    print(info[2], device.shell("su -c 'getprop sys.usb.config'"))
print("-----------------------------------")

### Check All Devices
devices = sorted(os.listdir("/sys/class/net/"))
devices = [dev for dev in devices if dev.startswith('qc')]
for i, info in enumerate(mobile_info):
    devices.append(info[2])

print("Device List:", devices)

time.sleep(4)

### Run MobileInsight
run_list = []
for i, dev in enumerate(devices):
    run_store = subprocess.Popen("sudo python3 monitor.py -d {} -b 9600".format(dev), shell=True, preexec_fn=os.setpgrp)
    run_list.append(run_store)

for item in run_list:
    print(item.pid)

# time.sleep(5)
print("Start logging...")
    
### Kill Python3 sessions when capturing KeyboardInterrupt
while True:
    try:
        time.sleep(1)  # detect every second
    except KeyboardInterrupt:
        os.system("ps -ef | grep python3 > ps_temp.txt")
        with open('ps_temp.txt', 'r') as fp:
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
            if info[7].startswith("python3 ./auto_monitor.py"):
                kill_list.append(info[1])
        for pid in kill_list[:-1]:
            os.system("sudo kill -9 {}".format(pid))
        os.system("sudo rm ps_temp.txt")
        os.system("sudo kill -9 {}".format(kill_list[-1]))
        break
    except Exception as e:
        print("error", e)

