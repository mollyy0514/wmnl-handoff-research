#! /usr/bin/sh

echo hello
sudo rmmod usbserial
sudo modprobe usbserial vendor=0x05c6 product=0x9091
echo hello