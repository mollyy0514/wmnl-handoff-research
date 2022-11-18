#! /usr/bin/sh

# getprop sys.usb.config
# setprop sys.usb.config diag,serial_cdev,rmnet,adb

sudo rmmod option
sudo rmmod usb_wwan
sudo rmmod usbserial

# sudo modprobe usbserial vendor=0x05c6 product=0x9091
sudo modprobe usbserial vendor=0x2c7c product=0x0800
sleep 1

adb devices
ls /dev/ttyUSB*
ls /dev/serial/by-id
