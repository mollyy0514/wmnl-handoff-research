#!/bin/bash

# Edit file "/etc/resolv.conf"
sudo vim /etc/resolv.conf
'''
# nameserver 127.0.0.53
m
options edns0 trust-ad
'''
