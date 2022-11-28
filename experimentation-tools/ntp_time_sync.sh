#! /usr/bin/sh

# sudo apt install ntp
echo "restart ntp.service"
sudo systemctl restart ntp.service
sleep 10

ntpq -p
sleep 4.5
ntpq -p
sleep 4.5

echo "stop ntp.service"
sudo systemctl stop ntp.service
sleep 1

ntpq -p
