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
    if (argc != 4) {
        printf("\n\
The correct command is:\n\
./client.o port bandwidth(unit kb) packet_length(unit byte):\n\
For example\n\
./client.o 3270 2896 362\n");
        assert(argc == 4);
    }
    int port = atoi(argv[1]);
    double bandwidth = atof(argv[2]) * 1000;
    int packet_length = atoi(argv[3]);
    int sock = 0;
    struct sockaddr_in serv_addr;
    char send_buf[1024] = {0};
    int seq = 0;
    uint total_time = 3600;
    double expected_packet_per_sec = bandwidth / (packet_length << 3);
    double sleeptime = 1.0 / expected_packet_per_sec;
    double prev_sleeptime = sleeptime;
	char filename[100];
    ofstream myfile;

	sprintf(filename, "c_port_%d_running.tmp", port);
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
 
    int enable = 1;
    setsockopt(sock, SOL_TCP, 42, &enable, sizeof(int));

    char scheduler[] = "redundant";
    setsockopt(sock, SOL_TCP, 43, scheduler, sizeof(scheduler));




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
        myfile.close();

        return -1;
    }


    string redundent = gen_random(packet_length);
    
    int count_packet = 0;
    int count_time = 1;
    for (int i=0; i<packet_length; i+=1)
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
        if (sendall(sock, send_buf, &packet_length) == -1) {
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

    cout << "finish\n";
    myfile.open(filename);
    myfile << "FINISH" << " " << getpid();
    close(sock);
    return 0;
}