# HOW TO RUN


1. in server end:
```
python3 server.py -p PORT
```
ex:
```
python3 server.py -p 3270
```

2. in client end

```
python3 client.py -H HOST_ADDRESS -p port
```

ex

```
python3 client.py -H 140.112.20.183 -p 3270
```


Or modify the default host adress and port in the code.

Some parameters such as
1. payload size
2. transmission rate
3. saving log path
can also be modified in the code.

```
# PARAMETERS ##################
length_packet = 400
bandwidth = 5000*1024 # unit kbps
total_time = 3600
pcap_path = "/home/wmnlab/D/pcap_data"
pcap_path = "./pcap_data"
ss_dir = "./ss"
cong = 'cubic'.encode()
##################################

```
