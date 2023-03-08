#!/usr/bin/env bash

if [ "$1" == "-a" ]; then
  cd ./jackbedford/wmnl-handoff-research/experimental-tools-beta/android
elif [ "$1" == "-m" ]; then
  cd ./jackbedford/wmnl-handoff-research/experimental-tools-beta/mobileinsight
elif [ "$1" == "-i" ]; then
  cd ./jackbedford/wmnl-handoff-research/experimental-tools-beta/iperf
elif [ "$1" == "-u" ]; then
  cd ./jackbedford/wmnl-handoff-research/experimental-tools-beta/udp-socket-programming
elif [ "$1" == "-t" ]; then
  cd ./jackbedford/wmnl-handoff-research/experimental-tools-beta/tcp-socket-programming
elif [ "$1" == "-q" ]; then
  cd ./jackbedford/wmnl-handoff-research/experimental-tools-beta/quectel
elif [ "$1" == "-g" ]; then
  cd ./jackbedford/wmnl-handoff-research/experimental-tools-beta/gps
elif [ "$1" == "-s" ]; then
  cd ./jackbedford/wmnl-handoff-research/experimental-tools-beta/sync
else
  cd ./jackbedford/wmnl-handoff-research/experimental-tools-beta
fi
