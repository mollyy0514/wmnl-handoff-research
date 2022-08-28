#!/usr/bin/python
# Filename: monitor-example.py
# Command usage:
# sudo python3 monitor-example.py SERIAL_PORT BAUD DEVICE_NAME
# sudo python3 monitor-example.py /dev/ttyUSB0 9600 sm00
import os
import sys
import datetime as dt

# Import MobileInsight modules
from mobile_insight.monitor import OnlineMonitor
from mobile_insight.analyzer import MsgLogger


if __name__ == "__main__":

    # Set Path
    dirpath = "./mi2log"
    if not os.path.exists(dirpath):
        os.mkdir(dirpath)

    if len(sys.argv) < 4:
        print("Error: please specify physical port name, baudrate, and device name.")
        print((__file__, "SERIAL_PORT_NAME BAUNRATE"))
        sys.exit(1)

    # Initialize a 3G/4G monitor
    src = OnlineMonitor()
    src.set_serial_port(sys.argv[1])  # the serial port to collect the traces
    src.set_baudrate(int(sys.argv[2]))  # the baudrate of the port

    # Save the monitoring results as an offline log
    now = dt.datetime.today()
    n = [str(x) for x in [now.year, now.month, now.day, now.hour, now.minute, now.second]]
    n = [x.zfill(2) for x in n]  # zero-padding to two digit
    n = '-'.join(n[:3]) + '_' + '-'.join(n[3:])
    savepath = os.path.join(dirpath, "diag_" + sys.argv[3] + '_' + n + ".mi2log")
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

    # Dump the messages to std I/O. Comment it if it is not needed.
    dumper = MsgLogger()
    dumper.set_source(src)
    dumper.set_decoding(MsgLogger.XML)  # decode the message as xml

    # Start the monitoring
    src.run()
