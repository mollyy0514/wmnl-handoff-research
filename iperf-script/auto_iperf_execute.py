# pip3 install adbutils

from adbutils import adb
from pprint import pprint

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

devices_info = []
for i, info in enumerate(adb.list()):
    try:
        devices_info.append((info.serial, info.state, serial_to_device[info.serial]))
    except:
        print("Unknown device: {} {}".format(info.serial, info.state))

devices_info = sorted(devices_info, key=lambda v:v[2])

devices = []
for i, info in enumerate(devices_info):
    devices.append(adb.device(info[0]))
    print("{} - {} {} {}".format(i+1, info[0], info[1], info[2]))

for device, info in zip(devices, devices_info):
    # print(info[2], device.shell("setprop sys.usb.config diag,serial_cdev,rmnet,adb"))
    print(info[2], device.shell("getprop sys.usb.config"))
    # # Set timeout for shell command
    # device.shell("sleep 1", timeout=0.5) # Should raise adbutils.AdbTimeout

for device, info in zip(devices, devices_info):
    print(info[2], device.shell("cd /sdcard/wmnl-handoff-research/iperf-script"))
    print(info[2], device.shell("ls"))