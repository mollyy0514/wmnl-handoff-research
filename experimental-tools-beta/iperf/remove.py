#!/usr/bin/env python3
import sys
import os
import datetime as dt

dirpath = "./log"
os.system("echo wmnlab | sudo -S su")

# dates = sorted(os.listdir(dirpath), reverse=True)
dates = sorted(os.listdir(dirpath))
print(dates.pop())