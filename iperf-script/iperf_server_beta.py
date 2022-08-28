import os
import sys
import datetime as dt
import time
import subprocess
import argparse
import signal


parser = argparse.ArgumentParser()
parser.add_argument("-p", "--port", type=int,
                    help="port to bind", default=3270)
parser.add_argument("-l", "--list_device", type=str, nargs='+',  # input list of devices sep by 'space'
                    help="list of device", default=["reserve"])
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

thread_stop = False
exit_program = False

pcap_path = "./server_pcap"
log_path = "./server_log"
if not os.path.exists(pcap_path):
    os.mkdir(pcap_path)
if not os.path.exists(log_path):
    os.mkdir(log_path)


if __name__ == '__main__':
    os.system("echo wmnlab | sudo -S su")
    print("All supported port: 3200-3300, even number for Uplink, odd number for Downlink. ")
    print("--------------------")

    port_list = []
    for device in args.list_device:
        port_list.append(device_to_port[device])

    now = dt.datetime.today()
    n = [str(x) for x in [now.year, now.month, now.day, now.hour, now.minute, now.second]]
    n = [x.zfill(2) for x in n]  # zero-padding to two digit
    n = '-'.join(n[:3]) + '_' + '-'.join(n[3:])

    _l = []
    run_list = []
    for device, port in zip(args.list_device, port_list):
        # _l.append("iperf3 -s 0.0.0.0 -p %d -V --logfile %s" % (port[0], os.path.join(log_path, "serverlog_UL_%d_%s_%s.log"%(port[0], device, n))))
        # _l.append("iperf3 -s 0.0.0.0 -p %d -V --logfile %s" % (port[1], os.path.join(log_path, "serverlog_UL_%d_%s_%s.log"%(port[1], device, n))))
        _l.append("iperf3 -s 0.0.0.0 -p %d -V" % port[0])
        _l.append("iperf3 -s 0.0.0.0 -p %d -V" % port[1])
        pcap_ul = os.path.join(pcap_path, "server_UL_%d_%s_%s.pcap"%(port[0], device, n))
        _l.append("tcpdump -i any port %d -w %s &" % (port[0], pcap_ul))
        pcap_dl = os.path.join(pcap_path, "server_DL_%d_%s_%s.pcap"%(port[1], device, n))
        _l.append("tcpdump -i any port %d -w %s &" % (port[1], pcap_dl))
    
    for l in _l: 
        print(l.split(" "))
        run_store = subprocess.Popen(l.split(" "), shell=True, preexec_fn=os.setpgrp)
        run_list.append(run_store)
    
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            # subprocess.Popen(["killall -9 iperf3"], shell=True, preexec_fn=os.setsid)
            for run_item in run_list:
                try:
                    print(run_item, ", PID: ", run_item.pid)
                    os.killpg(os.getpgid(run_item.pid), signal.SIGTERM)
                    # command = "sudo kill -9 -{}".format(run_item.pid)
                    # subprocess.check_output(command.split(" "))
                    break
                except Exception as e:
                    print(e)
        except Exception as e:
            print("error", e)
    