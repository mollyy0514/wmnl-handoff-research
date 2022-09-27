#!/usr/bin/env python3
# Command Usage:
# pip3 install adbutils
# ./set_mobile.py -d DEVICE_NAME
# ./set_mobile.py -d sm01
from adbutils import adb
import argparse
import sys

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--device", type=str,
                    help="device name (only allow 1 device)", required=True)
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
    # xm14":"",
    "xm15":"64545f94",
    "xm16":"613a273a",
    "xm17":"fe3df56f",
}

if adb.list()[0].state != "unauthorized":
    if args.device:
        device = adb.device(device_to_serial[args.device])
    else:
        device = adb.device()
else:
    print(args.device, "adbutils.errors.AdbError: device unauthorized.")
    sys.exit(1)

print(args.device, device)
print("-----------------------------------")

tools = ["git", "iperf3m", "iperf3", "python3", "tcpdump", "tmux", "vim"]  
print(device.shell("su -c 'cd /sdcard/wmnl-handoff-research && /data/git pull'"))
for tool in tools:
    if args.device[:2] == "sm":
        device.shell("su -c 'cp /sdcard/wmnl-handoff-research/script-sm/termux-tools/{} /bin'".format(tool))
        device.shell("su -c 'chmod +x /bin/{}'".format(tool))
    elif args.device[:2] == "xm":
        device.shell("su -c 'cp /sdcard/wmnl-handoff-research/script-xm/termux-tools/{} /sbin'".format(tool))
        device.shell("su -c 'chmod +x /sbin/{}'".format(tool))
print("-----------------------------------")

# test tools
print(device.shell("su -c 'iperf3 --version'"))
print("-----------------------------------")
print(device.shell("su -c 'iperf3m --version'"))
print("-----------------------------------")
print(device.shell("su -c 'tcpdump --version'"))
print("-----------------------------------")
print(device.shell("su -c 'git --version'"))
print("-----------------------------------")
print(device.shell("su -c 'python3 --version'"))
print("-----------------------------------")
print(device.shell("su -c 'tmux -V'"))
print("-----------------------------------")
print(device.shell("su -c 'vim --version'"))
print("-----------------------------------")
# print(device.shell("su -c 'iperf3m -c 140.112.20.183 -p 3270 -l 250 -b 200k -V -u'"))
