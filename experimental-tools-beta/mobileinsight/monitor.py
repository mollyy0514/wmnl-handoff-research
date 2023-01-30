#!/usr/bin/python
# Filename: monitor-example.py

# Command usage:
# sudo python3 monitor-example.py -d DEVICE_NAME -p SERIAL_PORT -b BAUD
# sudo python3 monitor-example.py -d sm00 -p /dev/ttyUSB0 -b 9600

import os
import sys
import datetime as dt
import argparse

# Import MobileInsight modules
from mobile_insight.monitor import OnlineMonitor
from mobile_insight.analyzer import MsgLogger

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--device", type=str,
                    help="device name (allows only 1 device)", default="unam")
parser.add_argument("-p", "--serial_port", type=str,
                    help="serial DM port")
parser.add_argument("-b", "--baud", type=int,
                    help="baudrate", default=9600)
args = parser.parse_args()

device_to_serial = {
    "sm00":"R5CRA1ET5KB",
    "sm01":"R5CRA1D2MRJ",
    "sm02":"R5CRA1GCHFV",
    "sm03":"R5CRA1JYYQJ",
    "sm04":"R5CRA1EV0XH",
    "sm05":"R5CRA1GBLAZ",
    "sm06":"R5CRA1ESYWM",
    "sm07":"R5CRA1ET22M",
    "sm08":"R5CRA2EGJ5X",
    "xm00":"73e11a9f",
    "xm01":"491d5141",
    "xm02":"790fc81d",
    "xm03":"e2df293a",
    "xm04":"28636990",
    "xm05":"f8fe6582",
    "xm06":"d74749ee",
    "xm07":"10599c8d",
    "xm08":"57f67f91",
    "xm09":"232145e8",
    "xm10":"70e87dd6",
    "xm11":"df7aeaf8",
    "xm12":"e8c1eff5",
    "xm13":"ec32dc1e",
    "xm14":"2aad1ac6",
    "xm15":"64545f94",
    "xm16":"613a273a",
    "xm17":"fe3df56f",
    "qc00":"76857c8" ,
    "qc01":"bc4587d" ,
    "qc02":"5881b62f",
    "qc03":"32b2bdb2",
}


if __name__ == "__main__":
    # Set Path
    now = dt.datetime.today()
    date = [str(x) for x in [now.year, now.month, now.day]]
    date = '-'.join(date)
    dirpath = "./log/{}/{}".format(date, "mi2log")  # mobileinsight log

    if args.device == "unam":
        if not args.serial_port:
            print("Error: please specify a valid serial DM port.")
            print(' '.join(["Usage: sudo python3", __file__, "<-d DEVICE_NAME> [-p SERIAL_PORT_NAME] [-b BAUNRATE]"]))
            print(' '.join(["       sudo python3", __file__, "<-p SERIAL_PORT_NAME> [-b BAUNRATE]"]))
            sys.exit(1)
    else:
        if args.device.startswith('sm'):
            args.serial_port = os.path.join("/dev/serial/by-id", "usb-SAMSUNG_SAMSUNG_Android_{}-if00-port0".format(device_to_serial[args.device]))
        elif args.device.startswith('qc'):
            args.serial_port = os.path.join("/dev/serial/by-id", "usb-Quectel_RM500Q-GL_{}-if00-port0".format(device_to_serial[args.device]))

    # Initialize a 3G/4G monitor
    src = OnlineMonitor()
    src.set_serial_port(args.serial_port)  # the serial port to collect the traces
    src.set_baudrate(args.baud)  # the baudrate of the port

    # Save the monitoring results as an offline log
    now = dt.datetime.today()
    n = [str(x) for x in [now.year, now.month, now.day, now.hour, now.minute, now.second]]
    n = [x.zfill(2) for x in n]  # zero-padding to two digit
    n = '-'.join(n[:3]) + '_' + '-'.join(n[3:])
    savepath = os.path.join(dirpath, "diag_log_{}_{}.mi2log".format(args.device, n))
    src.save_log_as(savepath)

    # src.enable_log_all()
    # Enable 3G/4G/5G messages to be monitored. Here we enable RRC (radio resource control) monitoring
    src.enable_log("5G_NR_RRC_OTA_Packet")
    src.enable_log("LTE_RRC_OTA_Packet")
    src.enable_log("WCDMA_RRC_OTA_Packet")
    # Enable other messages
    src.enable_log("LTE_RRC_Serv_Cell_Info")
    # src.enable_log("LTE_PHY_Serv_Cell_Measurement")
    # src.enable_log("LTE_PHY_Connected_Mode_Intra_Freq_Meas")
    # src.enable_log("LTE_PHY_Connected_Mode_Neighbor_Measurement")
    # Shen-ru's needed
    src.enable_log('5G_NR_ML1_Searcher_Measurement_Database_Update_Ext')
    src.enable_log('LTE_PHY_Connected_Mode_Intra_Freq_Meas')
    src.enable_log('LTE_PHY_Connected_Mode_Neighbor_Measurement')
    src.enable_log('LTE_PHY_Inter_RAT_Measurement')
    src.enable_log('LTE_PHY_Inter_Freq_Log')

    # Dump the messages to std I/O. Comment it if it is not needed.
    dumper = MsgLogger()
    dumper.set_source(src)
    dumper.set_decoding(MsgLogger.XML)  # decode the message as xml

    # Start the monitoring
    src.run()
