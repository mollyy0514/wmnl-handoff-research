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


parser = argparse.ArgumentParser()
parser.add_argument("-H", "--host", type=str,
                    help="server ip address", default="140.112.20.183")
                    # help="server ip address", default="210.65.88.213")
parser.add_argument("-d", "--device", type=str,                # enable both uplink & downlink
                    help="device name (only allow 1 device)", required=True)
parser.add_argument("-p", "--port", type=int, nargs='+',       # input list of port numbers sep by 'space'
                    help="port to bind")
parser.add_argument("-u", "--udp", action="store_true",        # needs not value, "True" if set "-u"
                    help="use UDP rather than TCP")
parser.add_argument("-b", "--bitrate", type=str,
                    help="target bitrate in bits/sec (0 for unlimited)", default=["200k", "1M"])
parser.add_argument("-l", "--length", type=str,
                    help="length of buffer to read or write in bytes (packet size)", default=["250", "1250"])
parser.add_argument("-t", "--time", type=int,
                    help="time in seconds to transmit for (default 1 hour = 3600 secs)", default=3600)
parser.add_argument("-S", "--stream", type=str,
                    help="stream flow: uplink (ul), downlink (dl), bi-link (default bl)", default="bl")
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
    "reserve": (3270, 3299),
}

serverip = args.host
device = args.device
if args.port:
    ports = args.port
else:
    ports = [device_to_port[args.device][0], device_to_port[args.device][1]]  # default setting

is_udp = "-u" if args.udp else ""

if type(args.bitrate) is list:  # unit: bps
    bitrate = args.bitrate[0] if args.udp else args.bitrate[1]
else:
    bitrate = args.bitrate
if type(args.length) is list:  # unit: bytes
    packet_size = args.length[0] if args.udp else args.length[1]
else:
    packet_size = args.length

max_time = args.time  # unit: second
stream_flow = args.stream
if stream_flow == "ul":
    is_reverse = ""
elif stream_flow == "dl":
    is_reverse = "-R"

pcap_path = "./client_pcap"
if not os.path.exists(pcap_path):
    os.mkdir(pcap_path)

log_path = "./client_log"
if not os.path.exists(log_path):
    os.mkdir(log_path)

now = dt.datetime.today()
n = [str(x) for x in [now.year, now.month, now.day, now.hour, now.minute, now.second]]
n = [x.zfill(2) for x in n]  # zero-padding to two digit
n = '-'.join(n[:3]) + '_' + '-'.join(n[3:])

_l = []
run_list = []
if len(ports) > 2:
    raise Exception("You cannot specify more than 2 ports for one device.")

if stream_flow == "bl":
    if len(ports) < 2:
        raise Exception("You need to specify at least 2 ports for bi-link transmission.")
    pcap_bl = os.path.join(pcap_path, "client_BL_{}_{}_{}_{}.pcap".format(ports[0], ports[1], device, n))
    tcpproc = "tcpdump -i any net {} -w {} &".format(serverip, pcap_bl)
    socket_proc1 = "iperf-3.9-m1 -c {} -p {} -b {} -l {} {} -t {} -V".format(serverip, ports[0], bitrate, packet_size, is_udp, max_time)
    socket_proc2 = "iperf-3.9-m1 -c {} -p {} -b {} -l {} {} -R -t {} -V".format(serverip, ports[1], bitrate, packet_size, is_udp, max_time)
    _l = [tcpproc, socket_proc1, socket_proc2]
else:
    port_ss = "_".join([str(port) for port in ports])
    pcap = os.path.join(pcap_path, "client_{}_{}_{}_{}.pcap".format(stream_flow.upper(), port_ss, device, n))
    tcpproc = "tcpdump -i any net {} -w {} &".format(serverip, pcap)
    _l.append(tcpproc)
    for port in ports:
        socket_proc = "iperf-3.9-m1 -c {} -p {} -b {} -l {} {} -t {} -V".format(serverip, port, bitrate, packet_size, is_udp, max_time)
        _l.append(socket_proc)

for l in _l: 
    print(l)
    run_store = subprocess.Popen(l, shell=True, preexec_fn=os.setpgrp)
    run_list.append(run_store)

while True:
    try:
        time.sleep(1)
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
