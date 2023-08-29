#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import time
import threading
import multiprocessing
import os
import sys
import datetime as dt
import argparse
import subprocess
import signal
from device_to_port import device_to_port


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--number_client", type=int,
                        help="number of client", default=1)
    parser.add_argument("-d", "--devices", type=str, nargs='+',
                        help="list of devices", default=["unam"])
    parser.add_argument("-p", "--ports", type=str, nargs='+',
                        help="ports to bind")
    parser.add_argument("-b", "--bitrate", type=str,
                        help="target bitrate in bits/sec (0 for unlimited)", default="1M")
    parser.add_argument("-l", "--length", type=str,
                        help="length of buffer to read or write in bytes (packet size)", default="250")
    parser.add_argument("-t", "--time", type=int,
                        help="time in seconds to transmit for (default 1 hour = 3600 secs)", default=3600)
    return parser.parse_args()

def create_device_list(devices):
    device_list = []
    for dev in devices:
        if '-' in dev:
            pmodel = dev[:2]
            start = int(dev[2:4])
            stop = int(dev[5:7]) + 1
            for i in range(start, stop):
                _dev = "{}{:02d}".format(pmodel, i)
                device_list.append(_dev)
            continue
        device_list.append(dev)
    return device_list

def create_port_list(args, devices):
    if not args.ports:
        return [(device_to_port[device][0], device_to_port[device][1]) for device in devices]
    else:
        port_list = []
        for port in args.ports:
            if '-' in port:
                start = int(port[:port.find('-')])
                stop = int(port[port.find('-') + 1:]) + 1
                port_list.extend(list(range(start, stop)))
            else:
                port_list.append(int(port))
        return port_list


# ===================== Main Process =====================

args = parse_arguments()

devices = create_device_list(args.devices)
ports = create_port_list(args, devices)

length_packet = int(args.length)

if args.bitrate[-1] == 'k':
    bitrate = int(args.bitrate[:-1]) * 1e3
elif args.bitrate[-1] == 'M':
    bitrate = int(args.bitrate[:-1]) * 1e6
else:
    bitrate = int(args.bitrate)

total_time = args.time
number_client = args.number_client

expected_packet_per_sec = bitrate / (length_packet << 3)
sleeptime = 1.0 / expected_packet_per_sec

print(devices)
print(ports)
print("bitrate:", bitrate)

# os.system("echo wmnlab | sudo -S su")
os.system("echo 00000000 | sudo -S su")


# ===================== Simple Socket =====================

# # 設定伺服器的主機和埠
# HOST = '127.0.0.1'
# PORT = 12345

# # 建立TCP伺服器
# server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# server_socket.bind((HOST, PORT))
# server_socket.listen(1)

# print('等待客戶端連線...')
# client_socket, client_address = server_socket.accept()
# print('已連線至:', client_address)

# while True:
#     data = client_socket.recv(1024)
#     if not data:
#         break
#     print('收到來自客戶端的訊息:', data.decode())
#     response = input('請輸入要回傳的訊息: ')
#     client_socket.sendall(response.encode())

# client_socket.close()
# server_socket.close()

# ===================== Parameters =====================
HOST = '0.0.0.0'
pcap_path = '/Users/jackbedford/temp'  # '/home/wmnlab/temp'

# ===================== Global Variables =====================
stop_threads = False
tcpproc_list = []

now = dt.datetime.today()
current_datetime = [str(x) for x in [now.year, now.month, now.day, now.hour, now.minute, now.second]]
current_datetime = [x.zfill(2) for x in current_datetime]  # zero-padding to two digit
current_datetime = '-'.join(current_datetime[:3]) + '_' + '-'.join(current_datetime[3:])

print(current_datetime)

def capture_traffic(devices, ports, pcap_path, current_datetime):
    for device, port in zip(devices, ports):
        pcap = os.path.join(pcap_path, f"server_pcap_BL_{device}_{port[0]}_{port[1]}_{current_datetime}_sock.pcap")
        # tcpproc = subprocess.Popen([f"tcpdump -i any port '({port[0]} or {port[1]})' -w {pcap}"], shell=True, preexec_fn=os.setpgrp)
        tcpproc = subprocess.Popen([f"sudo tcpdump -i any port '({port[0]} or {port[1]})' -w {pcap}"], shell=True, preexec_fn=os.setpgrp)
        tcpproc_list.append(tcpproc)
    time.sleep(1)

def kill_traffic_capture():
    print('Killing tcpdump process...')
    for tcpproc in tcpproc_list:
        # os.killpg(os.getpgid(tcpproc.pid), signal.SIGTERM)
        os.system(f"sudo kill -TERM -{tcpproc.pid}")
    time.sleep(1)

# capture_traffic(devices, ports, pcap_path, current_datetime)


rx_sockets = []
tx_sockets = []

for dev, port in zip(devices, ports):
    s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # server_socket
    # s1.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # s1.setsockopt(socket.IPPROTO_TCP, TCP_CONGESTION, cong)
    s1.bind((HOST, port[0]))
    s1.listen(1)  # Listen for incoming connections
    rx_sockets.append(s1)
    
    s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # server_socket
    # s2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # s2.setsockopt(socket.IPPROTO_TCP, TCP_CONGESTION, cong)
    s2.bind((HOST, port[1]))
    s2.listen(1)  # Listen for incoming connections
    tx_sockets.append(s2)

    print(f'Create socket at {HOST}:{port[0]} for UL...')
    print(f'Create socket at {HOST}:{port[1]} for DL...')

print('等待客戶端連線...')

tcp_addr = {}
rx_connections = []
tx_connections = []

def fill_tcp_conn_addr(s1, s2, device):
    conn, addr = s1.accept()  # client_socket 1, client_address 1
    print('Connection from:', addr)
    tcp_addr[s1] = addr
    rx_connections.append((conn, addr))
    
    # conn, addr = s2.accept()  # client_socket 2, client_address 2
    # print('Connection from:', addr)
    # tcp_addr[s2] = addr
    # tx_connections.append((conn, addr))
    
# Accept incoming connections
t_fills = []
print(rx_sockets)
print(tx_sockets)
for s1, s2, dev in zip(rx_sockets, tx_sockets, devices):
    fill_tcp_conn_addr(s1, s2, dev)
    # t = threading.Thread(target=fill_tcp_conn_addr, args=(s1, s2, dev, ))
    # t_fills.append(t)

print("successful!!")

# print(t_fills)

# for t in t_fills:
#     t.start()

# for t in t_fills:
#     t.join()











# try:
#     while True:
#         time.sleep(10)
        
# except KeyboardInterrupt:
#     stop_threads = True
#     kill_traffic_capture()
    
#     print('Successfully closed.')
#     sys.exit()

