#!/usr/bin/env python3

# from asyncio import subprocess
import socket
import time
import threading
import os
import datetime as dt
import argparse
import subprocess


#=================argument parsing======================
parser = argparse.ArgumentParser()
# parser.add_argument("-ps", "--port_start", type=int,
#                     help="port to bind, range: [start, end]", default=3280)
# parser.add_argument("-pe", "--port_end", type=int,
#                     help="port to bind, range: [start, end]", default=3287)
# parser.add_argument("-n", "--number_client", type=int,
#                     help="number of client", default=2)
# parser.add_argument("-l", "--length", type=int,
#                     help="payload length", default=250)
# parser.add_argument("-b", "--bandwidth", type=int,
#                     help="data rate (bits per second)", default=200000)   
# parser.add_argument("-t", "--time", type=int,
#                     help="maximum experiment time", default=3600)

parser.add_argument("-d", "--devices", type=str, nargs='+',  # input list of devices sep by 'space'
                    help="list of devices", default=["unam"])
# parser.add_argument("-H", "--host", type=str,
#                     help="server ip address", default="140.112.20.183")
#                     # help="server ip address", default="140.112.17.209")
#                     # help="server ip address", default="210.65.88.213")
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

devices = args.devices

# PORTS = [i for i in range(args.port_start, args.port_end+1)]
PORTS = []
for device in devices:
    PORTS.append((device_to_port[device][0]))  # default uplink port for each device

# UL_PORTS, DL_PORTS = [], []
# for device in devices:
#     UL_PORTS.append((device_to_port[device][0]))  # default uplink port for each device
#     DL_PORTS.append((device_to_port[device][1]))  # default downlink port for each device

# if type(args.bitrate) is list:  # unit: bps
#     bitrate = args.bitrate[0] if args.udp else args.bitrate[1]
# else:
#     bitrate = args.bitrate
# if type(args.length) is list:  # unit: bytes
#     packet_size = args.length[0] if args.udp else args.length[1]
# else:
#     packet_size = args.length

length_packet = int(args.length)

# bandwidth = args.bandwidth
if args.bitrate[-1] == 'k':
    bandwidth = int(args.bitrate[:-1]) * 1e3
elif args.bitrate[-1] == 'M':
    bandwidth = int(args.bitrate[:-1]) * 1e6
else:
    bandwidth = int(args.bitrate)

total_time = args.time
# number_client = args.number_client
# number_client = len(args.devices)
number_client = 1

expected_packet_per_sec = bandwidth / (length_packet << 3)
sleeptime = 1.0 / expected_packet_per_sec
#========================================================

#=================global variables=======================
thread_stop = True
exit_main_process = False
udp_addr = {}
#========================================================

#=================other variables========================
HOST = '0.0.0.0'
CONTROL_PORT = 3299
pcap_path = "pcapdir"
#========================================================

def connection_setup():
    print("Initial setting up...")
    
    s_udp_list = []
    s_udp_ul_list = []
    s_udp_dl_list = []
    conn_list = []
    
    #--------------establish sockets for UDP data traffic----- 
    for PORT in PORTS:
        s_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s_udp.bind((HOST, PORT))
        s_udp_list.append(s_udp)
    
    # for PORT in UL_PORTS:
    #     s_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #     s_udp.bind((HOST, PORT))
    #     s_udp_ul_list.append(s_udp)
    # for PORT in DL_PORTS:
    #     s_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #     s_udp.bind((HOST, PORT))
    #     s_udp_dl_list.append(s_udp)
    
    #--------------establish TCP control flows----------------
    s_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s_tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)    
    s_tcp.bind((HOST, CONTROL_PORT))

    # print(PORTS, "wait for tcp connection...")
    print((HOST, CONTROL_PORT), "wait for tcp control connection...")
    s_tcp.listen(number_client)

    for port in zip(PORTS):
        print((HOST, port), "wait for udp connection...")
    # for port1, port2 in zip(UL_PORTS, DL_PORTS):
    #     print((HOST, port1), "wait for udp connection...")
    #     print((HOST, port2), "wait for udp connection...")
    
    for i in range(number_client):
        conn, tcp_addr = s_tcp.accept()
        print('tcp Connected by', tcp_addr)
        conn_list.append(conn)
    
    # print((HOST, CONTROL_PORT), "wait for connection...")
    # s_tcp.listen(1)
    # conn, tcp_addr = s_tcp.accept()
    # print('tcp Connected by', tcp_addr)
    # print((host, port), "connection setup complete")
    # result[0] = s_tcp, conn, tcp_addr

    return s_tcp, s_udp_list, conn_list
    # return s_tcp, s_udp_ul_list, s_udp_dl_list, conn_list

def transmission(s_udp_list):
    global thread_stop
    global udp_addr
    print("start transmission: ")
    
    seq = 1
    prev_transmit = 0
    
    start_time = time.time()
    next_transmit_time = start_time + sleeptime
    
    time_slot = 1
    
    while time.time() - start_time < total_time and not thread_stop:
    
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
        
        for s_udp in s_udp_list:
            if s_udp in udp_addr.keys():
                s_udp.sendto(outdata, udp_addr[s_udp])
        seq += 1
        
        if time.time()-start_time > time_slot:
            print("[%d-%d]"%(time_slot-1, time_slot), "transmit", seq-prev_transmit)
            time_slot += 1
            prev_transmit = seq
            
    
    print("---transmission timeout---")
    print("transmit", seq, "packets")


def receive(s_udp):
    s_udp.settimeout(3)
    print("wait for indata...")
    number_of_received_packets = 0
    
    seq = 1
    max_seq = 1

    global thread_stop
    global udp_addr
    while not thread_stop:
        try:
            #receive data, update client's addresses (after receiving, server know where to transmit)
            indata, addr = s_udp.recvfrom(1024)
            udp_addr[s_udp] = addr                     
            
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
    print("STOP bypass")

os.system("echo wmnlab | sudo -S su")
while not exit_main_process:
    if not os.path.exists(pcap_path):
        os.system("mkdir %s"%(pcap_path))


    now = dt.datetime.today()
    n = '-'.join([str(x) for x in[ now.year, now.month, now.day, now.hour, now.minute, now.second]])
    
    #Create subprocesses to capture packets (TCPDUMP)
    tcpproc_list = []
    tcpproc =  subprocess.Popen(["sudo tcpdump -i any port 3299 -w %s/%s_%s.pcap"%(pcap_path,PORT, n)], shell=True, preexec_fn = os.setpgrp)
    tcpproc_list.append(tcpproc)
    for PORT in PORTS:
        tcpproc =  subprocess.Popen(["sudo tcpdump -i any port %s -w %s/%s_%s.pcap"%(PORT, pcap_path,PORT, n)], shell=True, preexec_fn = os.setpgrp)
        tcpproc_list.append(tcpproc)
    # for PORT in UL_PORTS:
    #     tcpproc =  subprocess.Popen(["sudo tcpdump -i any port %s -w %s/%s_%s.pcap"%(PORT, pcap_path,PORT, n)], shell=True, preexec_fn = os.setpgrp)
    #     tcpproc_list.append(tcpproc)
    # for PORT in DL_PORTS:
    #     tcpproc =  subprocess.Popen(["sudo tcpdump -i any port %s -w %s/%s_%s.pcap"%(PORT, pcap_path,PORT, n)], shell=True, preexec_fn = os.setpgrp)
    #     tcpproc_list.append(tcpproc)
        
    time.sleep(1)
    
    receiving_threads = []
    udp_addr = {}

    try:
        s_tcp, s_udp_list, conn_list = connection_setup()
        # s_tcp, s_udp_ul_list, s_udp_dl_list, conn_list = connection_setup()
        
        while thread_stop == True:
            control_message = input("Enter START to start: ")
            if control_message == "START":
                thread_stop = False
                
                for conn in conn_list:
                    conn.sendall("START".encode())
                t = threading.Thread(target = transmission, args = (s_udp_list, ))
                # t = threading.Thread(target = transmission, args = (s_udp_dl_list, ))
                t.start()
                for s_udp in s_udp_list:
                # for s_udp in s_udp_ul_list:
                    t1 = threading.Thread(target = receive, args = (s_udp,))
                    t1.start()
                    receiving_threads.append(t1)
        
    except KeyboardInterrupt as inst:
        print("keyboard interrupt: ")
        #Kill TCPDUMP subprocesses
        for tcpproc in tcpproc_list:
            pgid = os.getpgid(tcpproc.pid)
    
            command = "sudo kill -9 -{}".format(pgid)
            subprocess.check_output(command.split(" "))
        exit()
    except Exception as e:
        print("Connection Error:", e)
        exit()
    

    try:
        while t.is_alive():
            control_message = input("Enter STOP to stop: ")
            if control_message == "STOP":
                thread_stop = True
                for conn in conn_list:
                    conn.sendall("STOP".encode())
                break
            elif control_message == "EXIT":
                thread_stop = True
                exit_main_process = True
                for conn in conn_list:
                    conn.sendall("EXIT".encode())
                break    
    except Exception as e:
        print(e)
        exit_main_progress = True
    finally:
        print("finally")
        
        thread_stop = True
        
        #end transmission and receive threads
        t.join()
        for t1 in receiving_threads:
            t1.join()
        
        #close sockets
        s_tcp.close()
        for s_udp in s_udp_list:
            s_udp.close()
        # for s_udp in s_udp_ul_list:
        #     s_udp.close()
        # for s_udp in s_udp_dl_list:
        #     s_udp.close()
            
        #Kill TCPDUMP subprocesses
        for tcpproc in tcpproc_list:
            pgid = os.getpgid(tcpproc.pid)
    
            command = "sudo kill -9 -{}".format(pgid)
            subprocess.check_output(command.split(" "))
