import socket
import time
import csv
import sys

HOST = '140.112.20.183'
PORT = 3299

# client
if sys.argv[1] == '-c':
    with open('device.txt', 'r', encoding='utf-8') as f:
        device = f.readline().strip()
    print(device)
    
    server_addr = (HOST, PORT)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(3)
    num_packet_per_round = 100
    packet_interval = 0

    timestamp_client = []
    timestamp_server = []

    i = 0
    tmo_cnt = 0
    while i <= num_packet_per_round:
        time0 = time.time()
        outdata = str(i).zfill(3)
        s.sendto(outdata.encode(), server_addr)
        s.settimeout(3)
        try:
            indata, addr = s.recvfrom(1024)
            time1 = time.time()
            indata = indata.decode()
            tmo_cnt = 0
        except:
            print("timeout", outdata)
            tmo_cnt += 1
            if tmo_cnt == 3:
                break
            continue
        # print('recvfrom ' + str(addr) + ': ' + indata)
        print(outdata, time0, time1, "RTT =", (time1-time0)*1000, "ms")
        timestamp_client.append([outdata, time0, time1])
        timestamp_server.append(indata.split(' '))
        time.sleep(packet_interval)
        i += 1
    outdata = 'end'
    s.sendto(outdata.encode(), server_addr)

    with open('sync_client_'+device+'.csv', 'w') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerows(timestamp_client)
    with open('sync_server_'+device+'.csv', 'w') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerows(timestamp_server)

# server
elif sys.argv[1] == '-s':
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('0.0.0.0', PORT))

    while True:
        print('server start at: %s:%s' % ('0.0.0.0', PORT))
        print('wait for connection...')

        while True:
            indata, addr = s.recvfrom(1024)
            time0 = time.time()
            indata = indata.decode()
            if indata == 'end':
                break
            print('recvfrom ' + str(addr) + ': ' + indata)
            
            time1 = time.time()
            outdata = f'{indata} {time0} {time1}'
            s.sendto(outdata.encode(), addr)
            print(indata, time0, time1)
