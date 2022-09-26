# wmnl-handoff-research
Utils and analysis code for research in handoff.

## Reload mobile tools for smartphone

Enter adb shell with laptop or use **Termux** app on the smartphone

	$ adb shell 

Enter super user privilege

	$ su

Update git repository

	# cd /sdcard/wmnl-handoff-research
	# /data/git pull

### Xiaomi 10T (xm)

Reload termux tools to /sbin

	# cp script-xm/termux-tools/* /sbin
	# chmod +x /sbin/*

### Samsung Galaxy A42 5G (sm)

Reload termux tools to /bin

	# cp script-sm/termux-tools/* /bin
	# chmod +x /bin/*

## iPerf3 & TcpDump Usage
[***iPerf3 Manual***](https://iperf.fr/iperf-doc.php)

### Server

	$ ssh USERNAME@SERVER_IP -p 8000

	// window 1: capture all packets throught specific net interface
	$ cd ~/D/YOUR_DIRECTORY
	$ tcpdump -i any port PORT(3280-3299) -w FILENAME.pcap

	// window 2: open a port to listen
	$ iperf3 -s -B 0.0.0.0 -p PORT(3280-3299)

### Client
	
	$ su

	// window 1: capture all packets throught specific net interface
	# cd /sdcard/YOUR_DIRECTORY
	$ tcpdump -i any net SERVER_IP -w FILENAME.pcap

	// window 2: transmit & receive customized packets
	$ iperf3 -c SERVER_IP -p PORT(3280-3299) -b BITRATE(bps) -l PACKET_LENGTH(bytes) -t EXP_TIME(seconds) [-u](TCP->UDP) [-R](UPLINK->DOWNLINK)
