#!/usr/bin/env python3
# Command Usage:
# pip3 install adbutils
# ./auto_mi_iperf.py
from adbutils import adb
import os
import sys
import datetime as dt
import argparse
import time
from pprint import pprint

# parser = argparse.ArgumentParser()
# parser.add_argument("-d", "--devices", type=str, nargs='+',  # input list of devices sep by 'space'
#                     help="list of devices", default=["unnamed"])
# args = parser.parse_args()

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
    # "":"xm14",
    "64545f94":"xm15",
    "613a273a":"xm16",
    "fe3df56f":"xm17",
    "76857c8" :"quectel0",
    "bc4587d" :"quectel1",
    "5881b62f":"quectel2",
    "32b2bdb2":"quectel3",
}

os.system("echo wmnlab | sudo -S su")

devices_info = []
for i, info in enumerate(adb.list()):
    try:
        if info.state == "device":
            # <serial> <device|offline> <device name>
            devices_info.append((info.serial, info.state, serial_to_device[info.serial]))
        else:
            print("Unauthorized device {}: {} {}".format(serial_to_device[info.serial], info.serial, info.state))
    except:
        print("Unknown device: {} {}".format(info.serial, info.state))

devices_info = sorted(devices_info, key=lambda v:v[2])

devices = []
for i, info in enumerate(devices_info):
    devices.append(adb.device(info[0]))
    print("{} - {} {} {}".format(i+1, info[0], info[1], info[2]))
print("-----------------------------------")

for info in adb.list():
    if info.state == "unauthorized":
        sys.exit(1)

# getprop
for device, info in zip(devices, devices_info):
    print(info[2], device.shell("su -c 'getprop sys.usb.config'"))

# run mobileinsight
mi_path = os.path.join("/home/wmnlab-yj/Desktop/Jackbedford/wmnl-handoff-research", "iperf-script", "monitor-example.py")
for device, info in zip(devices, devices_info):
    device_path = os.path.join("/dev/serial/by-id", "usb-SAMSUNG_SAMSUNG_Android_{}-if00-port0".format(info[0]))
    os.system("sudo python3 {} {} 9600 {} &".format(mi_path, device_path, info[2]))
    
# Kill python3 if capture KeyboardInterrup
while True:
    try:
        time.sleep(1)  # detect every second
    except KeyboardInterrupt:
        # subprocess.Popen(["killall -9 iperf3"], shell=True, preexec_fn=os.setsid)
        # for run_item in run_list:
        #     print(run_item, ", PID: ", run_item.pid)
        #     os.killpg(os.getpgid(run_item.pid), signal.SIGTERM)
        #     # command = "kill -9 -{}".format(run_item.pid)
        #     # subprocess.check_output(command.split(" "))
        os.system("sudo killall -9 python3")
        break
    except Exception as e:
        print("error", e)
