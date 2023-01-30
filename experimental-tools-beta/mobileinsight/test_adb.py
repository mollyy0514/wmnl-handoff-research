#!/usr/bin/env python3

# Command Usage:
# pip3 install adbutils
# ./auto_monitor.py

from adbutils import adb
import os
import sys
import time
import subprocess
import datetime as dt
import threading

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
print("----------------------------------------------")


class myThread (threading.Thread):
    def __init__(self, threadID, dev, device):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.dev = dev
        self.device = device
    def run(self):
        # print ("开始线程：" + self.name)
        print(self.dev)
        run_iperf(self.dev, self.device)
        # print ("退出线程：" + self.name)

def run_iperf(dev, device):
    print(dev, device.shell(f"""su -c 'cd /sdcard/wmnl-handoff-research \n
                                    ls \n
                                    cd experimentation-tools/iperf \n
                                    python3 client.py -d {dev}'"""))

class myThread1(threading.Thread):
    def __init__(self, adb_handles, mobile_info):
        threading.Thread.__init__(self)
        # self.threadID = threadID
        self.adb_handles = adb_handles
        self.mobile_info = mobile_info
    def run(self):
        # print ("开始线程：" + self.name)
        # print(self.dev)
        stop_iperf(self.adb_handles, self.mobile_info)
        # print ("退出线程：" + self.name)

def stop_iperf(adb_handles, mobile_info):
    key_interupt = False
    while True:
        try:
            time.sleep(1)
            print(time.time())
        except KeyboardInterrupt:
            print("************************************************")
            for i, (device, info) in enumerate(zip(adb_handles, mobile_info)):
                print(info[2], device.shell(f"""
                                            su -c 'pkill iperf3 \n
                                                    pkill tcpdump \n
                                                    pkill python3'
                                        """))
            key_interupt = True
            print("hi")
            break

# TODO
threads = [None]*len(adb_handles)
for i, (device, info) in enumerate(zip(adb_handles, mobile_info)):
    threads[i] = threading.Thread(target = run_iperf, args = (info[2], device))

for l in threads:
    l.start()
    time.sleep(0.0001)

while True:
    try:
        time.sleep(1)
        # print(time.time())
    except KeyboardInterrupt:
        print("************************************************")
        for i, (device, info) in enumerate(zip(adb_handles, mobile_info)):
            print(info[2], device.shell(f"""
                                        su -c 'pkill iperf3 \n
                                                pkill tcpdump \n
                                                pkill python3'
                                    """))
        key_interupt = True
        print("hi")
        break


# for i, (device, info) in enumerate(zip(adb_handles, mobile_info)):
#     # print(info[2], device.shell("su -c 'python3 /sdcard/wmnl-handoff-research/experimentation-tools/iperf/client.py -d sm05'"))
#     threads[i] = myThread(i, info[2], device)

# stop_thread = myThread1(adb_handles, mobile_info)

# for i in range(len(adb_handles)):
#     threads[i].daemon = True

# stop_thread.daemon = True

# stop_thread.start()
# for i in range(len(adb_handles)):
#     threads[i].start()
#     # threads[i].join()

# stop_thread.join()
# for i in range(len(adb_handles)):
#     # threads[i].start()
#     threads[i].join()

print("Victory!!")
