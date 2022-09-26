# wmnl-handoff-research
utils and analysis code for research in handoff.

## Reload mobile tools for smartphone

Enter adb shell with laptop or use "Termux" app on xm phone
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
	# cp script-xm/termux-tools/* /bin
	# chmod +x /bin/*
