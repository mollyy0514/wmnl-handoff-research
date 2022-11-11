#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import time
import threading
import datetime as dt
import sys
import os
import argparse
import subprocess

#====================argument parsing==============================
parser = argparse.ArgumentParser()
# parser.add_argument("-ps", "--port_start", type=int,
#                     help="port to bind, range: [start, end]", default=3280)
# parser.add_argument("-pe", "--port_end", type=int,
#                     help="port to bind, range: [start, end]", default=3287)
# parser.add_argument("-m", "--multiple_interfaces", type=int,
#                     help="0: w/o multiple interfaces; 1: multiple interfaces", default=1)
# parser.add_argument("-l", "--length", type=int,
#                     help="payload length", default=250)
# parser.add_argument("-b", "--bandwidth", type=int,
#                     help="data rate (bits per second)", default=200000)   
# parser.add_argument("-t", "--time", type=int,
#                     help="maximum experiment time", default=3600)

parser.add_argument("-d", "--devices", type=str, nargs='+',  # input list of devices sep by 'space'
                    help="list of devices", default=["unam"])
parser.add_argument("-H", "--host", type=str,
                    help="server ip address", default="140.112.20.183")
                    # help="server ip address", default="140.112.17.209")
                    # help="server ip address", default="210.65.88.213")
# parser.add_argument("-p", "--ports", type=int, nargs='+',     # input list of port numbers sep by 'space'
#                     help="ports to bind")
# parser.add_argument("-u", "--udp", action="store_true",       # needs no value, True if set "-u"
#                     help="use UDP rather than TCP")           # default TCP
parser.add_argument("-b", "--bitrate", type=str,
                    help="target bitrate in bits/sec (0 for unlimited)", default="1M")
parser.add_argument("-l", "--length", type=str,
                    help="length of buffer to read or write in bytes (packet size)", default="250")
parser.add_argument("-t", "--time", type=int,
                    help="time in seconds to transmit for (default 1 hour = 3600 secs)", default=3600)
args = parser.parse_args()

device_to_port = {
    "xm00": (3230, 3231),
    "xm01": (3232, 3233),
    "xm02": (3234, 3235),
    "xm03": (3236, 3237),
    "xm04": (3238, 3239),
    "xm05": (3240, 3241),
    "xm06": (3242, 3243),
    "xm07": (3244, 3245),
    "xm08": (3246, 3247),
    "xm09": (3248, 3249),
    "xm10": (3250, 3251),
    "xm11": (3252, 3253),
    "xm12": (3254, 3255),
    "xm13": (3256, 3257),
    "xm14": (3258, 3259),
    "xm15": (3260, 3261),
    "xm16": (3262, 3263),
    "xm17": (3264, 3265),
    "sm00": (3200, 3201),
    "sm01": (3202, 3203),
    "sm02": (3204, 3205),
    "sm03": (3206, 3207),
    "sm04": (3208, 3209),
    "sm05": (3210, 3211),
    "sm06": (3212, 3213),
    "sm07": (3214, 3215),
    "sm08": (3216, 3217),
    "qc00": (3270, 3271),
    "qc01": (3272, 3273),
    "qc02": (3274, 3275),
    "qc03": (3276, 3277),
    "unam": (3280, 3281),
}

# if args.multiple_interfaces == 0:
#     try:
#         f = open("port.txt", "r")
#         l = f.readline()
#         PORT = int(l)
#     except:
#         PORT = input("First time running... please input the port number: ")
#         f = open("port.txt", "w")
#         f.write(PORT)
#     PORTS = [PORT]
# else:
#     PORTS = [i for i in range(args.port_start, args.port_end+1)]
# print("PORTS = ", PORTS)

devices = args.devices
UL_PORTS, DL_PORTS = [], []
for device in devices:
    UL_PORTS.append((device_to_port[device][0]))  # default uplink port for each device
    DL_PORTS.append((device_to_port[device][1]))  # default downlink port for each device

# length_packet = args.length
# bandwidth = args.bandwidth

length_packet = int(args.length)

# bandwidth = args.bandwidth
if args.bitrate[-1] == 'k':
    bandwidth = int(args.bitrate[:-1]) * 1e3
elif args.bitrate[-1] == 'M':
    bandwidth = int(args.bitrate[:-1]) * 1e6
else:
    bandwidth = int(args.bitrate)

total_time = args.time
HOST = args.host

expected_packet_per_sec = bandwidth / (length_packet << 3)
sleeptime = 1.0 / expected_packet_per_sec
#==================================================================

#===================global variables===============================
thread_stop = True
exit_main_process = False
#==================================================================

#===================other variables================================
CONTROL_PORT = 3299

pcap_path = "pcapdir"
if not os.path.exists(pcap_path):
    os.system("mkdir %s"%(pcap_path))
#==================================================================

def connection_setup():
    print("Initial setting up...")
    
    s_udp_list = []
    
    #--------------establish sockets for UDP data traffic----- 
    for device, port1, port2 in zip(devices, UL_PORTS, DL_PORTS):
        s_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s_udp.settimeout(1)
        
        #if m=1, bind to specific interface name
        # if args.multiple_interfaces == 1:
        #     interface_name = 'ss0'+str(PORT%10) #'usb' + str(index)
        #     print(interface_name)
        #     s_udp.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, (interface_name+'\0').encode())
        interface_name = device  #'ss0'+str(PORT%10) #'usb' + str(index)
        print(interface_name)
        s_udp.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, (interface_name+'\0').encode())
        # s_udp.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, (device+'\0').encode())
        
        s_udp_list.append(s_udp)
        
    #--------------establish TCP control flows----------------
    s_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s_tcp.connect((HOST, CONTROL_PORT))
    
    return s_tcp, s_udp_list

def transmission(s_udp_list):
    global thread_stop
    print("start transmission: ")
    
    seq = 1
    prev_transmit = 0
    
    start_time = time.time()
    next_transmit_time = start_time + sleeptime
    
    time_slot = 1
    
    while time.time() - start_time < total_time and not thread_stop:
        try:
            t = time.time()
            while t < next_transmit_time:
                t = time.time()
            next_transmit_time = next_transmit_time + sleeptime

            euler = 271828
            pi = 31415926
            datetimedec = int(t)
            microsec = int((t - int(t))*1000000)
        
            # redundant = os.urandom(length_packet-4*3)
            # outdata = datetimedec.to_bytes(4, 'big') + microsec.to_bytes(4, 'big') + seq.to_bytes(4, 'big') + redundant

            redundant = os.urandom(length_packet-4*5)
            outdata = euler.to_bytes(4, 'big') + pi.to_bytes(4, 'big') + datetimedec.to_bytes(4, 'big') + microsec.to_bytes(4, 'big') + seq.to_bytes(4, 'big') + redundant
            
            for s_udp, PORT in zip(s_udp_list, UL_PORTS):       
                s_udp.sendto(outdata, (HOST, PORT))
            seq += 1
        
            if time.time()-start_time > time_slot:
                print("[%d-%d]"%(time_slot-1, time_slot), "transmit", seq-prev_transmit)
                time_slot += 1
                prev_transmit = seq
        except Exception as e:
            print(e)
            thread_stop = True
    thread_stop = True
    print("---transmission timeout---")
    print("transmit", seq, "packets")

def receive(s_udp, s_udp_list):
    s_udp.settimeout(3)
    print("wait for indata...")
    number_of_received_packets = 0
    
    seq = 1
    max_seq = 1

    global thread_stop
    while not thread_stop:
        try:
            indata, addr = s_udp.recvfrom(1024)
            
            if len(indata) != length_packet:
                print("packet with strange length: ", len(indata))

            # seq = int(indata.hex()[16:24], 16)
            seq = int(indata.hex()[32:40], 16)
            max_seq = max(max_seq, seq)
            
            # ts = int(int(indata.hex()[0:8], 16)) + float("0." + str(int(indata.hex()[8:16], 16)))
            ts = int(int(indata.hex()[16:24], 16)) + float("0." + str(int(indata.hex()[24:32], 16)))
            
            number_of_received_packets += 1
            
        except Exception as inst:
            print("Error: ", inst)
            thread_stop = True
    thread_stop = True
    
    print("---Experiment Complete---")
    print("Total capture: ", number_of_received_packets, "Total loss: ", max_seq - number_of_received_packets)
    
    # for s_udp_list_element, port in zip(s_udp_list, DL_PORTS):
    #     if s_udp_list_element == s_udp:
    #         f = open(str(port)+".txt", "a")
    #         f.write("Total capture: " + str(number_of_received_packets) + "; Total loss: " + str(max_seq - number_of_received_packets) + "\n")
    #         f.close()
            
    print("STOP bypass")

def remote_control(s_tcp, t):
    global thread_stop
    global exit_main_process
    
    while t.is_alive() and not thread_stop:
        try:
            indata, addr = s_tcp.recvfrom(1024)    ###might need to check
            
            if indata.decode() == "STOP":    
                thread_stop = True
                break
            elif indata.decode() == "EXIT":
                thread_stop = True
                exit_main_process = True
                break
        except Exception as inst:
            print("Error: ", inst)
    thread_stop = True
    print("STOP remote control")

os.system("echo wmnlab | sudo -S su")
while not exit_main_process:
    tcpproc_list = []
    try:
        now = dt.datetime.today()
        n = '-'.join([str(x) for x in[ now.year, now.month, now.day, now.hour, now.minute, now.second]])
        # print(len(PORTS))
        # for PORT in PORTS:
        #     tcpproc = subprocess.Popen(["tcpdump -i any port %s -w %s/%s_%s.pcap"%(PORT,pcap_path,PORT,n)], shell=True, preexec_fn=os.setpgrp)
        #     tcpproc_list.append(tcpproc)
        print(len(UL_PORTS))
        for PORT in UL_PORTS:
            tcpproc = subprocess.Popen(["tcpdump -i any port %s -w %s/%s_%s.pcap"%(PORT,pcap_path,PORT,n)], shell=True, preexec_fn=os.setpgrp)
            tcpproc_list.append(tcpproc)
        print(len(DL_PORTS))
        for PORT in DL_PORTS:
            tcpproc = subprocess.Popen(["tcpdump -i any port %s -w %s/%s_%s.pcap"%(PORT,pcap_path,PORT,n)], shell=True, preexec_fn=os.setpgrp)
            tcpproc_list.append(tcpproc)
        print("ready to setup connection...")
        s_tcp, s_udp_list = connection_setup()
        
        #------------------wait for server ways "START"----------------
        while thread_stop == True:
            indata, addr = s_tcp.recvfrom(1024)    ###might need to check
            
            if indata.decode() == "START":    
                thread_stop = False
    except KeyboardInterrupt as inst:
        print("keyboard interrupt: ")
        for tcpproc in tcpproc_list:
            pgid = os.getpgid(tcpproc.pid)
    
            command = "kill -9 -{}".format(pgid)
            subprocess.check_output(command.split(" "))
        exit()
    except Exception as inst:
        print("Error: ", inst)
        pgid = os.getpgid(tcpproc.pid)
    
        command = "kill -9 -{}".format(pgid)
        subprocess.check_output(command.split(" "))
        exit()
    
    #--------------------start threads-------------------
    receiving_threads = []
    
    t = threading.Thread(target=transmission, args=(s_udp_list, ))
    t3 = threading.Thread(target=remote_control, args = (s_tcp, t))
    t.start()
    t3.start()
    
    for s_udp in s_udp_list:
        t2 = threading.Thread(target=receive, args=(s_udp, s_udp_list, ))
        t2.start()
        receiving_threads.append(t2)
    
    t.join()
    t3.join()

    #------------------wait for threads end-------------
    for t2 in receiving_threads:
        t2.join()

    s_tcp.close()
    for s_udp in s_udp_list:
        s_udp.close()

    print("finally: kill tcpdump")
    for tcpproc in tcpproc_list:
        pgid = os.getpgid(tcpproc.pid)
    
        command = "kill -9 -{}".format(pgid)
        subprocess.check_output(command.split(" "))
    
    time.sleep(5)
