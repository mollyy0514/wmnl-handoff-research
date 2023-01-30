#! /usr/bin/sh

# Edit File: "/etc/modprobe.d/blacklist.conf"
"""
### sudo vim /etc/modprobe.d/blacklist.conf
blacklist pl2303
### sudo reboot (optional)
### However, gps module needs pl2303!
""" 

# getprop sys.usb.config  # (rndis,adb)
# setprop sys.usb.config diag,serial_cdev,rmnet,adb

# lsmod
# lsmod | grep usbserial

sudo rmmod pl2303
sudo rmmod option
sudo rmmod usb_wwan
sudo rmmod usbserial
sleep 1

sudo modprobe usbserial vendor=0x05c6 product=0x9091
# sudo modprobe usbserial vendor=0x2c7c product=0x0800
sleep 1

adb devices
ls /dev/serial/by-id
