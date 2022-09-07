#! /usr/bin/sh

sudo rmmod option
sudo rmmod usb_wwan
sudo rmmod usbserial
sudo modprobe usbserial vendor=0x05c6 product=0x9091

ls /dev/ttyUSB*
ls /dev/serial/by-id
