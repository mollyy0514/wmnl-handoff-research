# Command usage (need su priviledge): 
# (1) python3 iperf_client_single.py -d DEVICE [-u]
#     python3 iperf_client_single.py -d sm01 -u
# (2) python3 iperf_client_single.py -d DEVICE -H SERVER_IP -p LIST_PORTS -S STREAMING_DIRECTION
#     python3 iperf_client_single.py -d sm01 -H 140.112.17.209 -p 3270 3271 -S bl
# (3) python3 iperf_client_single.py -d DEVICE -b BITRATE -l PACKET_SIZE -t EXP_TIME
#     python3 iperf_client_single.py -d sm01 -b 2M -l 2500 -t 300
import os
import sys
import time
import socket
import threading
import datetime as dt
import argparse
import subprocess
import re
import signal

# ------------------------------ Add Arguments & Global Variables ------------------------------- #
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--device", type=str,
                    help="device name (only allow 1 device)", default="unnamed")
parser.add_argument("-H", "--host", type=str,
                    help="server ip address", default="140.112.20.183")
                    # help="server ip address", default="140.112.17.209")
                    # help="server ip address", default="210.65.88.213")
parser.add_argument("-p", "--ports", type=int, nargs='+',     # input list of port numbers sep by 'space'
                    help="ports to bind")
parser.add_argument("-u", "--udp", action="store_true",       # needs no value, True if set "-u"
                    help="use UDP rather than TCP")           # default TCP
parser.add_argument("-b", "--bitrate", type=str,
                    help="target bitrate in bits/sec (0 for unlimited)", default=["200k", "200k"])  # [UDP, TCP]
parser.add_argument("-l", "--length", type=str,
                    help="length of buffer to read or write in bytes (packet size)", default=["250", "250"])  # [UDP, TCP]
parser.add_argument("-t", "--time", type=int,
                    help="time in seconds to transmit for (default 1 hour = 3600 secs)", default=3600)
parser.add_argument("-S", "--stream", type=str,
                    help="streaming direction: uplink (ul), downlink (dl), bi-link (bl, 2 ports/device)", default="bl")
parser.add_argument("-L", "--logfile", action="store_true",
                    help="save iperf output to logfile")
parser.add_argument("-K", "--keywords", type=str,
                    help="keywords for socket statistics", default=["bytes_sent", "cwnd"])
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
    "unam": (3268, 3269),
}

# ----------------------------------------- Parameters ------------------------------------------ #
thread_stop = False
# exit_program = False

serverip = args.host
device = args.device
if args.ports:
    ports = args.ports
    if args.stream == "bl" and len(ports) != 2:
        raise Exception("must specify at least and only 2 ports for the device to transmit bi-link.")
    elif (args.stream == "ul" or args.stream == "dl") and len(ports) != 1:
        raise Exception("must specify at least and only 1 port for the device to transmit uplink or downlink.")
else:
    ports = [device_to_port[device][0], device_to_port[device][1]]  # default port setting for each device

is_udp = "-u" if args.udp else ""

if type(args.bitrate) is list:  # unit: bps
    bitrate = args.bitrate[0] if args.udp else args.bitrate[1]
else:
    bitrate = args.bitrate
if type(args.length) is list:  # unit: bytes
    packet_size = args.length[0] if args.udp else args.length[1]
else:
    packet_size = args.length

if args.stream == "ul":
    is_reverse = ""
elif args.stream == "dl":
    is_reverse = "-R"

# check whether it has iperf3m
if os.path.exists("/bin/iperf3m") or os.path.exists("/sbin/iperf3m"):
    iperf = "iperf3m"
else:
    iperf = "iperf3"

# ----------------------------------------- Save Path ------------------------------------------- #
pcap_path = "./client_pcap"  # packet capture
if not os.path.exists(pcap_path):
    os.mkdir(pcap_path)

log_path = "./client_log"   # iperf log
if not os.path.exists(log_path):
    os.mkdir(log_path)

ss_path = "./client_stats"  # socket statistics (Linux: ss)
if not os.path.exists(ss_path):
    os.mkdir(ss_path)

# ----------------------------------- Define Utils Function ------------------------------------- #
def get_ss(device, port, mode):
    global thread_stop
    global n
    global args

    # fp = None
    fp = open(os.path.join(ss_path, "client_stats_{}_{}_{}_{}.csv".format(mode.upper(), device, port, n)), 'a+')
    print(fp)
    while not thread_stop:
        # ss --help (Linux/Android)
        # ss -ai src :PORT (server-side command)
        # ss -ai dst :PORT (client-side command)
        proc = subprocess.Popen(["ss -ai dst :{}".format(port)], stdout=subprocess.PIPE, shell=True)
        text = proc.communicate()[0].decode()
        lines = text.split('\n')
        for line in lines:
            if any(s in line for s in args.keywords):  # change the keywords if needed
                l = line.strip()
                fp.write(",".join([str(dt.datetime.now())]+ re.split("[: \n\t]", l))+'\n')
                break
        time.sleep(1)
    fp.close()

# ---------------------------------- Transmission / Receiving ----------------------------------- #
# Get time
now = dt.datetime.today()
n = [str(x) for x in [now.year, now.month, now.day, now.hour, now.minute, now.second]]
n = [x.zfill(2) for x in n]  # zero-padding to two digit
n = '-'.join(n[:3]) + '_' + '-'.join(n[3:])

_l = []          # command list
ss_threads = []  # ss thread command list
if args.stream == "bl":  # bi-link
    # tcpdump
    pcap_bl = os.path.join(pcap_path, "client_pcap_BL_{}_{}_{}_{}.pcap".format(device, ports[0], ports[1], n))
    tcpproc = "tcpdump -i any net {} -w {} &".format(serverip, pcap_bl)
    # iperf
    log1 = os.path.join(log_path, "client_log_UL_{}_{}_{}.log".format(device, ports[0], n))
    log2 = os.path.join(log_path, "client_log_UL_{}_{}_{}.log".format(device, ports[1], n))
    if args.logfile:
        socket_proc1 = "{} -c {} -p {} -b {} -l {} {} -t {} -V --logfile {}".format(iperf, serverip, ports[0], bitrate, packet_size, is_udp, args.time, log1)
        socket_proc2 = "{} -c {} -p {} -b {} -l {} {} -R -t {} -V --logfile {}".format(iperf, serverip, ports[1], bitrate, packet_size, is_udp, args.time, log2)
    else:
        socket_proc1 = "{} -c {} -p {} -b {} -l {} {} -t {} -V".format(iperf, serverip, ports[0], bitrate, packet_size, is_udp, args.time)
        socket_proc2 = "{} -c {} -p {} -b {} -l {} {} -R -t {} -V".format(iperf, serverip, ports[1], bitrate, packet_size, is_udp, args.time)
    _l = [tcpproc, socket_proc1, socket_proc2]
    # ss
    ss_threads.append(threading.Thread(target = get_ss, args = (device, ports[0], 'ul')))
    ss_threads.append(threading.Thread(target = get_ss, args = (device, ports[1], 'dl')))
elif args.stream == "ul" or args.stream == "dl":  # uplink or downlink
    # tcpdump
    pcap = os.path.join(pcap_path, "client_pcap_{}_{}_{}_{}.pcap".format(args.stream.upper(), device, ports[0], n))
    tcpproc = "tcpdump -i any net {} -w {} &".format(serverip, pcap)
    # iperf
    log = os.path.join(log_path, "client_log_{}_{}_{}_{}.log".format(args.stream.upper(), device, ports[0], n))
    if args.logfile:
        socket_proc = "{} -c {} -p {} -b {} -l {} {} -t {} -V --logfile {}".format(iperf, serverip, ports[0], bitrate, packet_size, is_udp, args.time, log)
    else:
        socket_proc = "{} -c {} -p {} -b {} -l {} {} -t {} -V".format(iperf, serverip, ports[0], bitrate, packet_size, is_udp, args.time)
    _l = [tcpproc, socket_proc]
    # ss
    ss_threads.append(threading.Thread(target = get_ss, args = (device, ports[0], args.stream)))
else:
    raise Exception("must specify from {ul, dl, bl}.")

# Run all commands in the collection
run_list = []  # running session list
for l in ss_threads:
    l.start()
    time.sleep(0.00001)
for l in _l: 
    print(l)
    run_store = subprocess.Popen(l, shell=True, preexec_fn=os.setpgrp)
    run_list.append(run_store)

# Kill iperf3 & tcpdump sessions with PID when detecting KeyboardInterrupt (Ctrl-C,Z)
while True:
    try:
        time.sleep(1)  # detect every second
    except KeyboardInterrupt:
        # subprocess.Popen(["killall -9 iperf3"], shell=True, preexec_fn=os.setsid)
        for run_item in run_list:
            print(run_item, ", PID: ", run_item.pid)
            os.killpg(os.getpgid(run_item.pid), signal.SIGTERM)
            # command = "kill -9 -{}".format(run_item.pid)
            # subprocess.check_output(command.split(" "))
        break
    except Exception as e:
        print("error", e)

thread_stop = True
