import socket
import time
import csv
import sys

HOST = '140.112.20.183'
PORT = 3299

# client
if sys.argv[1] == '-c':
    server_addr = (HOST, PORT)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(3)
    num_packet_per_round = 100
    packet_interval = 0

    time_stamp = []

    i = 0
    while i <= num_packet_per_round:
        time0 = time.time()
        outdata = str(i).zfill(3)
        s.sendto(outdata.encode(), server_addr)
        s.settimeout(3)
        try:
            indata, addr = s.recvfrom(1024)
            time1 = time.time()
            indata = indata.decode()
        except:
            print("timeout", outdata[:3])
            continue
        print('recvfrom ' + str(addr) + ': ' + indata)
        print(outdata[:3], time0, time1, "RTT =", (time1-time0)*1000, "ms")
        time_stamp.append([time0, time1])
        time.sleep(packet_interval)
        i += 1
    outdata = "end"
    s.sendto(outdata.encode(), server_addr)

    with open('sync_client_'+sys.argv[2]+'.csv', 'w') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerows(time_stamp)
    
    f.close()


# server
elif sys.argv[1] == '-s':
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('0.0.0.0', PORT))

    print('server start at: %s:%s' % ('0.0.0.0', PORT))
    print('wait for connection...')

    f = open('sync_server_'+sys.argv[2]+'.csv', 'w')
    csv_writer = csv.writer(f)

    while True:
        indata, addr = s.recvfrom(1024)
        time0 = time.time()
        indata = indata.decode()
        if indata == 'end':
            break
        print('recvfrom ' + str(addr) + ': ' + indata[:3])
        
        time1 = time.time()
        outdata = f'{indata[:3]} {time0} {time1}'
        s.sendto(outdata.encode(), addr)
        print(outdata[:3], time0, time1)
        csv_writer.writerow([outdata[:3], time0, time1])

    f.close()
