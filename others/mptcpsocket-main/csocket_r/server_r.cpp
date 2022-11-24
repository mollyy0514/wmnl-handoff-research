// Server side C/C++ program to demonstrate Socket
// programming
#include <netinet/in.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
#include <time.h>
#include <chrono>
#include <thread>
#include <iomanip>
#include <sstream>
#include <iostream>
#include <netinet/tcp.h>
#include <fstream>
#include <cassert>

using namespace std;

int sendall(int s, char *buf, int *len)
{
    int total = 0;        // how many bytes we've sent
    int bytesleft = *len; // how many we have left to send
    int n;
    int nc = 0;
    while(total < *len) {
        n = send(s, buf+total, bytesleft, 0);
        if (n <= -1) { 
            return -1;
        }
        if (n == 0) {
            nc += 1;
            cout << "nc " << nc << endl;
        }
        total += n;
        bytesleft -= n;
    }

    *len = total; // return number actually sent here

    return n==-1?-1:0; // return -1 on failure, 0 on success
}

string int_to_hex(int i )
{
    stringstream stream;
    stream << "0x" 
        << setfill ('0') << setw(sizeof(int)*2) 
        << hex << i;
    return stream.str();
}

uint64_t timeSinceEpochMillisec() {
  using namespace std::chrono;
  return duration_cast<milliseconds>(system_clock::now().time_since_epoch()).count();
}


string gen_random(const int len) {
    static const char alphanum[] =
        "0123456789"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz";
    std::string tmp_s;
    tmp_s.reserve(len);

    for (int i = 0; i < len; ++i) {
        tmp_s += alphanum[rand() % (sizeof(alphanum) - 1)];
    }
    
    return tmp_s;
}

int main(int argc, char const* argv[])
{

    if (argc != 4) {
        printf("\n\
The correct command is:\n\
./server_r.o port bandwidth(unit kb) packet_length(unit byte):\n\
For example\n\
./server_r.o 3270 2896 362\n");
        assert(argc == 4);
    }
    int port = atoi(argv[1]);
    double bandwidth = atof(argv[2]) * 1000;
    int packet_length = atoi(argv[3]);
	int total_time = 3600;
	int server_fd, new_socket;
	struct sockaddr_in address;
	int opt = 1;
	int addrlen = sizeof(address);
    char send_buf[1024] = {0};
	int seq = 0;
	int timeout_in_seconds = 15;
	int PORT = atoi(argv[1]);

    double expected_packet_per_sec = bandwidth / (packet_length << 3);
    double sleeptime = 1.0 / expected_packet_per_sec;
    double prev_sleeptime = sleeptime;

	ofstream myfile;
	char filename[100];
	sprintf(filename, "sr_port_%d_running.tmp", PORT);
	cout << "create socket " << PORT << endl;
	myfile.open (filename);
	myfile << "IDLE" << " " << getpid();
	myfile.close();
	if ((server_fd = socket(AF_INET, SOCK_STREAM, 0))
		== 0) {
		perror("socket failed");
		myfile.open (filename);
		myfile << "FAIL" << " " << getpid();
		exit(EXIT_FAILURE);
	}

    int enable = 1;
    setsockopt(server_fd, SOL_TCP, 42, &enable, sizeof(int));

    // char scheduler[] = "redundant";
    // setsockopt(server_fd, SOL_TCP, 43, scheduler, sizeof(scheduler));


	if (setsockopt(server_fd, SOL_SOCKET,
				SO_REUSEADDR | SO_REUSEPORT, &opt,
				sizeof(opt))) {
		perror("setsockopt");

		myfile.open (filename);
		myfile << "FAIL" << " " << getpid();
		exit(EXIT_FAILURE);
	}
	address.sin_family = AF_INET;
	address.sin_addr.s_addr = INADDR_ANY;
	address.sin_port = htons(PORT);

	// Forcefully attaching socket to the port 8080
	if (bind(server_fd, (struct sockaddr*)&address,
			sizeof(address))
		< 0) {
		perror("bind failed");
		myfile.open (filename);
		myfile << "FAIL" << " " << getpid();
		exit(EXIT_FAILURE);
	}
	if (listen(server_fd, 3) < 0) {
		perror("listen failed");
		myfile.open (filename);
		myfile << "FAIL" << " " << getpid();
		exit(EXIT_FAILURE);
	}
	if ((new_socket
		= accept(server_fd, (struct sockaddr*)&address,
				(socklen_t*)&addrlen))
		< 0) {
		perror("accept failed");
		myfile.open (filename);
		myfile << "FAIL" << " " << getpid();
		exit(EXIT_FAILURE);
	}

	cout << "connection establishment\n";
	myfile.open (filename);
	myfile << "RUNNING" << " " << getpid();
	myfile.close();

    string redundent = gen_random(packet_length);
    for (int i=0; i<packet_length; i+=1) {
        send_buf[i] = redundent[i];
    }


	// LINUX
    struct timeval tv;      
	tv.tv_sec = timeout_in_seconds;
    tv.tv_usec = 0;
    
    setsockopt (new_socket, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof tv);

    int count_packet = 0;
    int count_time = 1;
    for (int i=0; i<362; i+=1)
        send_buf[i] = redundent[i];
    strcpy((char *)redundent.c_str(), send_buf);
    auto now = chrono::steady_clock::now();
    auto ts = timeSinceEpochMillisec();
    auto start_time = chrono::steady_clock::now();

    do {
        for(int i=0; i<4; i+=1) {
            send_buf[11-i] = (seq >> i*8)& 0xFF;
        }

        now = chrono::steady_clock::now();
        ts = timeSinceEpochMillisec();
        for(int i=0; i<8; i+=1) {
            send_buf[7-i] = (ts >> i*8)& 0xFF;
        }
        if (sendall(new_socket, send_buf, &packet_length) == -1) {
            cout << "sendfail" << endl;
            myfile.open(filename);
            myfile << "FAIL" << " " << getpid();
            myfile.close();
            exit(-1);
        }
        seq += 1;
        count_packet += 1;
        this_thread::sleep_for(std::chrono::nanoseconds((int) (1000*1000*1000 * sleeptime)));
        if (chrono::duration_cast<chrono::seconds>(now - start_time).count() >= count_time ) {
            int tx_bytes = count_packet * packet_length;
			if (tx_bytes <= 1024*1024)
                printf("%d\t[%d-%d]\t%g kbps\n", port, count_time-1, count_time, 1.0*tx_bytes/1024*8);
            else
                printf("%d\t[%d-%d]\t%g Mbps\n", port, count_time-1, count_time, 1.0*tx_bytes/1024/1024*8);
            count_time += 1;
            sleeptime = (sleeptime +  prev_sleeptime * count_packet / expected_packet_per_sec) / 2;
            prev_sleeptime = sleeptime;
            count_packet = 0;
        }
    } while (chrono::duration_cast<chrono::seconds>(now - start_time).count() < total_time);

	myfile.open (filename);
	myfile << "FINISH" << " " << getpid();
	cout << "finish\n";
	myfile.close();
	return 0;
}
