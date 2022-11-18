#! /usr/bin/sh

# sudo apt install ntp
echo "restart ntp.service"
sudo systemctl restart ntp.service
sleep 10

ntpq -p
sleep 3
ntpq -p
sleep 3

echo "stop ntp.service"
sudo systemctl stop ntp.service