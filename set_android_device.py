#!/usr/bin/env python3
# Command Usage:
# ./set_android_device ADB_COMMAND
# ./set_android_device adb shell
# 1 - R5CRA1ET22M [device usb:1-4.4 product:a42xqxx model:SM_A426B device:a42xq transport_id:13] sm07
# 2 - R5CRA2EGJ5X [device usb:1-4.3 product:a42xqxx model:SM_A426B device:a42xq transport_id:14] sm08

import subprocess
import sys
import os

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
}

def parse_device_list(str):
    raw_list = [x.decode("utf-8") for x in str.splitlines() if x != b''][1:]
    devices = []
    for raw_device in raw_list:
        parts = raw_device.split()
        try:
            devices.append((parts[0], " ".join(parts[1:]), serial_to_device[parts[0]]))
        except:
            devices.append((parts[0], " ".join(parts[1:]), ""))
    if not devices:
        devices = None
    return devices

def get_device_list():
    p = subprocess.Popen(['adb', 'devices', '-l'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if len(err) == 0:
        return parse_device_list(out)
    else:
        return

def print_device_list(devices):
    for i in range(len(devices)):
        id, name, device = devices[i]
        print("%d - %s [%s] %s" % (i+1, id, name, device))

def num(s):
    try:
        return int(s)
    except:
        return s


devices = get_device_list()

if devices == None:
    print("Could not find any device")
    sys.exit(1)

print_device_list(devices)

if len(sys.argv) == 1:
    print("Please specify an adb command.")
    sys.exit(1)

while True:
    if len(devices) == 1:
        choosen = 1
        break
    choosen = num(sys.stdin.readline())
    if type(choosen) is not int:
        print("Please specify a number.")
        print_device_list(devices)
        continue
    if (choosen != None and choosen > 0 and choosen <= len(devices)):
        break

os.environ['ANDROID_SERIAL'] = devices[choosen - 1][0]

p = subprocess.Popen(sys.argv[1:])
try:
	p.communicate()
except KeyboardInterrupt:
	pass
