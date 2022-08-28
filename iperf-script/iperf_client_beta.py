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
parser.add_argument("-p", "--port", type=int,
                    help="port to bind", default=3270)
parser.add_argument("-H", "--HOST", type=str,
                    help="server ip address", default="140.112.20.183")
                    # help="server ip address", default="210.65.88.213")
parser.add_argument("-d", "--device", type=str,
                    help="device name", default="reserve")
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

device = args.device
port1 = device_to_port[args.device][0]
port2 = device_to_port[args.device][1]
serverip = args.HOST
thread_stop = False
exit_program = False
length_packet = 250  # unit: byte
bandwidth = 200      # unit: kbps
total_time = 3600    # unit: second

pcap_path = "./client_pcap"
log_path = "./client_log"
if not os.path.exists(pcap_path):
    os.mkdir(pcap_path)
if not os.path.exists(log_path):
    os.mkdir(log_path)


now = dt.datetime.today()
n = [str(x) for x in [now.year, now.month, now.day, now.hour, now.minute, now.second]]
n = [x.zfill(2) for x in n]  # zero-padding to two digit
n = '-'.join(n[:3]) + '_' + '-'.join(n[3:])

socket_proc1 =  subprocess.Popen(["iperf-3.9-m1 -c %s -p %d -b %dk -t 3600"%(serverip, port1, bandwidth)], shell=True, preexec_fn=os.setsid)
socket_proc2 =  subprocess.Popen(["iperf-3.9-m1 -c %s -p %d -b %dk -R -t 3600"%(serverip, port2, bandwidth)], shell=True, preexec_fn=os.setsid)

# pcap_ul = os.path.join(pcap_path, "client_UL_%d_%s_%s.pcap"%(port1, device, n))
# tcpproc =  subprocess.Popen(["tcpdump -i any net %s -w %s &"%(serverip, pcap_ul)], shell=True, preexec_fn=os.setsid)
# pcap_dl = os.path.join(pcap_path, "client_DL_%d_%s_%s.pcap"%(port2, device, n))
# tcpproc =  subprocess.Popen(["tcpdump -i any net %s -w %s &"%(serverip, pcap_dl)], shell=True, preexec_fn=os.setsid)
pcap_bl = os.path.join(pcap_path, "client_BL_%d_%d_%s_%s.pcap"%(port1, port2, device, n))
tcpproc =  subprocess.Popen(["tcpdump -i any net %s -w %s &"%(serverip, pcap_bl)], shell=True, preexec_fn=os.setsid)

while True:
    try:
        time.sleep(1)
    except KeyboardInterrupt:
        # subprocess.Popen(["killall -9 iperf3"], shell=True, preexec_fn=os.setsid)
        os.killpg(os.getpgid(socket_proc1.pid), signal.SIGTERM)
        os.killpg(os.getpgid(socket_proc2.pid), signal.SIGTERM)
        os.killpg(os.getpgid(tcpproc.pid), signal.SIGTERM)
        break
    except Exception as e:
        print("error", e)

# os.killpg(os.getpgid(tcpproc.pid), signal.SIGTERM)
