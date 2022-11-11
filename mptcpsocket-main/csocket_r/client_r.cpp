// Client side C/C++ program to demonstrate Socket
// programming
#include <arpa/inet.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
#include <string>
#include <chrono>
#include <thread>
#include <iomanip>
#include <sstream>
#include <time.h>
#include <iostream>
#include <unistd.h>
#include <netinet/tcp.h>
#include <assert.h>
#include <fstream>

using namespace std; 

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

int sendall(int s, char *buf, int *len)
{
    int total = 0;        // how many bytes we've sent
    int bytesleft = *len; // how many we have left to send
    int n;

    while(total < *len) {
        n = send(s, buf+total, bytesleft, 0);
        if (n == -1) { break; }
        total += n;
        bytesleft -= n;
    }

    *len = total; // return number actually sent here

    return n==-1?-1:0; // return -1 on failure, 0 on success
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
    if (argc != 2) {
        printf("\n\
The correct command is:\n\
./client_r.o port\n\
For example\n\
./client_r.o 3270\n");
        assert(argc == 4);
    }
    int port = atoi(argv[1]);
    int sock = 0, valread;
    struct sockaddr_in serv_addr;
    char buffer[4096] = { 0 };
	char filename[100];
	int timer_c = 1;
    int timeout_in_seconds = 10;
    ofstream myfile;

	sprintf(filename, "cr_port_%d_running.tmp", port);
    myfile.open (filename);
    myfile << "START" << " " << getpid();
    myfile.close();
    string seq_str = "";
    if ((sock = socket(AF_INET, SOCK_STREAM, 0)) < 0) {
        printf("\n Socket creation error \n");
        myfile.open (filename);
        myfile << "FAIL" << " " << getpid();


        return -1;
    }
 
	struct timeval tv;
	tv.tv_sec = timeout_in_seconds;
	tv.tv_usec = 0;
	setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, (const char*)&tv, sizeof(tv));


    int enable = 1;
    setsockopt(sock, SOL_TCP, 42, &enable, sizeof(int));

    // char scheduler[] = "redundant";
    // setsockopt(sock, SOL_TCP, 43, scheduler, sizeof(scheduler));




    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(port);
 
    // Convert IPv4 and IPv6 addresses from text to binary
    // form
    if (inet_pton(AF_INET, "140.112.20.183", &serv_addr.sin_addr)
        <= 0) {
        printf(
            "\nInvalid address/ Address not supported \n");

        myfile.open (filename);
        myfile << "FAIL" << " " << getpid();
		exit(EXIT_FAILURE);


        return -1;
    }
 
    if (connect(sock, (struct sockaddr*)&serv_addr,
                sizeof(serv_addr))
        < 0) {
        printf("\nConnection Failed \n");
        myfile.open(filename);
        myfile << "FAIL" << " " << getpid();
        return -1;
    }

    
    double recv_bytes = 0;
    auto start_time = chrono::steady_clock::now();

	while (true) {
		valread = read(sock, buffer, 1024);
		if (valread==0) {
			cout << "other side close" << endl;
			break;
		}
		else if (valread < 0) {
			cout << "connection timeout" << endl;
			break;
		}
		recv_bytes += valread;
        auto now = chrono::steady_clock::now();
		// printf("%s\n", buffer);
		if (chrono::duration_cast<chrono::seconds>(now - start_time).count() >= timer_c) {
			if (recv_bytes <= 1024*1024) {
				printf("%d\t[%d-%d]\t%g kbps\n", port, timer_c-1, timer_c, recv_bytes/1024*8);
			}
			else {
				printf("%d\t[%d-%d]\t%g Mbps\n", port, timer_c-1, timer_c, recv_bytes/1024/1024*8);
			}
			recv_bytes = 0;
			timer_c += 1;
		}
	}

    cout << "finish\n";
    myfile << "FINISH" << " " << getpid();
    close(sock);
    return 0;
}