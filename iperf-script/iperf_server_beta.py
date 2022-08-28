# Command usage:
# python3 iperf_server_beta.py -d LIST_DEVICES
# python3 iperf_server_beta.py -d LIST_DEVICES -p LIST_PORTS -S STREAMING_DIRECTION
import os
import sys
import datetime as dt
import time
import subprocess
import argparse
import signal

# ------------------------------ Add Arguments & Global Variables ------------------------------- #
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--devices", type=str, nargs='+',  # input list of devices sep by 'space'
                    help="list of devices", required=True)
parser.add_argument("-p", "--ports", type=int, nargs='+',    # input list of port numbers sep by 'space'
                    help="ports to bind")
parser.add_argument("-S", "--stream", type=str,
                    help="streaming direction: uplink (ul), downlink (dl), bi-link (default bl)", default="bl")
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

# ----------------------------------------- Parameters ------------------------------------------ #
devices = args.devices
if args.ports:
    ports = args.ports
    if args.stream == "bl" and len(ports) != 2*len(devices):
        raise Exception("must specify 2 ports for each device to transmit bi-link.")
    elif (args.stream == "ul" or args.stream == "dl") and len(ports) != len(devices):
        raise Exception("must specify only 1 port for each device to transmit uplink or downlink.")
    else:
        raise Exception("must specify only ul, dl, bl.")
else:
    for device in devices:
        ports = []
        ports.append((device_to_port[device][0]))  # default uplink port for each device
        ports.append((device_to_port[device][1]))  # default downlink port for each device

# ----------------------------------------- Save Path ------------------------------------------- #
pcap_path = "./server_pcap"
if not os.path.exists(pcap_path):
    os.mkdir(pcap_path)

log_path = "./server_log"
if not os.path.exists(log_path):
    os.mkdir(log_path)

# ---------------------------------- Transmission / Receiving ----------------------------------- #
if __name__ == '__main__':
    # Avoid need to feed in password for superuser priviledge
    os.system("echo wmnlab | sudo -S su")

    print("Supported port: 3200-3300, even number for Uplink, odd number for Downlink.")
    print("---------------------------------------------------------------------------")

    # Get time
    now = dt.datetime.today()
    n = [str(x) for x in [now.year, now.month, now.day, now.hour, now.minute, now.second]]
    n = [x.zfill(2) for x in n]  # zero-padding to two digit
    n = '-'.join(n[:3]) + '_' + '-'.join(n[3:])

    _l = []        # commands list
    run_list = []  # running sessions list
    if args.stream == "bl":  # bi-link
        for device, port1, port2 in zip(devices, ports[::2], ports[1::2]):
            # tcpdump
            pcap_ul = os.path.join(pcap_path, "server_UL_{}_{}_{}.pcap".format(port1, device, n))
            _l.append("tcpdump -i any port {} -w {} &".format(port1, pcap_ul))
            pcap_dl = os.path.join(pcap_path, "server_DL_{}_{}_{}.pcap".format(port2, device, n))
            _l.append("tcpdump -i any port {} -w {} &".format(port2, pcap_dl))
            # iperf
            _l.append("iperf3 -s -B 0.0.0.0 -p {} -V".format(port1))
            _l.append("iperf3 -s -B 0.0.0.0 -p {} -V".format(port2))
    else:  # uplink or downlink
        for device, port in zip(devices, ports):
            # tcpdump
            pcap = os.path.join(pcap_path, "server_{}_{}_{}_{}.pcap".format(args.stream.upper(), port, device, n))
            _l.append("tcpdump -i any port {} -w {} &".format(port, pcap))
            # iperf
            _l.append("iperf3 -s -B 0.0.0.0 -p {} -V".format(port))
    
    # Run all commands in the collection
    for l in _l: 
        print(l)
        run_store = subprocess.Popen(l, shell=True, preexec_fn=os.setpgrp)
        run_list.append(run_store)
    
    # Kill iperf3 & tcpdump sessions with PID when detecting KeyboardInterrupt (Ctrl-C,Z)
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            # subprocess.Popen(["killall -9 iperf3"], shell=True, preexec_fn=os.setsid)
            for run_item in run_list:
                print(run_item, ", PID: ", run_item.pid)
                os.killpg(os.getpgid(run_item.pid), signal.SIGTERM)
                # command = "sudo kill -9 -{}".format(run_item.pid)
                # subprocess.check_output(command.split(" "))
            break
        except Exception as e:
            print("error", e)
    