#!/usr/bin/env bash

if [ "$1" == "-a" ]; then
  cd ./experimental-tools-beta/android
elif [ "$1" == "-m" ]; then
  cd ./experimental-tools-beta/mobileinsight
elif [ "$1" == "-i" ]; then
  cd ./experimental-tools-beta/iperf
elif [ "$1" == "-u" ]; then
  cd ./experimental-tools-beta/udp-socket-programming
elif [ "$1" == "-t" ]; then
  cd ./experimental-tools-beta/tcp-socket-programming
elif [ "$1" == "-q" ]; then
  cd ./experimental-tools-beta/quectel
elif [ "$1" == "-g" ]; then
  cd ./experimental-tools-beta/gps
elif [ "$1" == "-s" ]; then
  cd ./experimental-tools-beta/sync
else
  cd ./experimental-tools-beta
fi
