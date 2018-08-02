#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <signal.h>
#include <netdb.h>
#include <fcntl.h>
#include <time.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/select.h>
#include <sys/time.h>
#include <sys/socket.h>
#include "moonskySocket.h"

#define MYPORT "9999"
#define MAXBUFLEN 10240

int main(int argc, char **argv) {
    printf("**************************************************************\n");
    for (int i = 0; i < argc; i++) {
        printf("argv[%d]: %s\n", i, argv[i]);
    }
    printf("**************************************************************\n");
    server *client = (server*)malloc(sizeof(server));
    int sockfd = listenOnUDPSocket(MYPORT);
    if (sockfd < 0) {
        return EXIT_FAILURE;
    }
    printf("Listining on Port %s\n", MYPORT);
    printf("Waiting for incoming UDP message\n");
    client->sockfd = sockfd;
    char buf[MAXBUFLEN];

    recvUDPMessage(client, buf, MAXBUFLEN);

    int iTotalMsg = 0;
    int pktSize = 0;
    int interval = 0;
    int ulcount = 0;

    sscanf(buf, "#%d#%d#%d#%d", &iTotalMsg, &pktSize, &interval, &ulcount);

    printf("Received No.%d heart beat: totalmsg: %d, pktSize: %d, interval: %d\n",
            ulcount, iTotalMsg, pktSize, interval);

    char *input;
    input = (char*)malloc(sizeof(*input) * 128);
    fd_set readfds;
    fd_set tempReadfds;
    FD_ZERO(&readfds);
    FD_SET(0, &readfds);
    FD_SET(sockfd, &readfds);
    struct timeval tv;
    tv.tv_sec = 0;
    tv.tv_usec = interval;

    int icount = 0;
    int pcount = 0; // Number of 16kB packet
    char content[pktSize];
    memset(content, '*', pktSize);
    content[pktSize] = '\0';

    int fdMax = sockfd;
    int waiting = 0;
    

    for(;;)
    {
        tempReadfds = readfds;
        int rv = select(fdMax+1, &tempReadfds, NULL, NULL, &tv);
        if (rv == 0)
        {
            if (waiting != 0) {
                continue;
            }
            icount++;
            // tv timeout
            char temp[10];
            sprintf(temp, "#%d#", ulcount);
            strncpy(content, temp, strlen(temp));
            if (sendUDPMessage(client, content) == EXIT_SUCCESS)
                printf("Send msg %d in response to %d\n", icount, ulcount);
            tv.tv_usec = interval; // After 0.016ms, send another 1kB packet
            tv.tv_sec = 0;
            if (icount == iTotalMsg) {
                icount = 0;
                waiting = 1;
                // tv.tv_sec = 10;
                printf("All pkts are sent, waiting for incoming UDP message\n");
            }
        }
        else if (FD_ISSET(0, &tempReadfds))
        {
            fgets(input, 128, stdin);
            free(input);
            close(client->sockfd);
            free(client);
            return(EXIT_SUCCESS);
        }
        else {
            // coming msg from client
             recvUDPMessage(client, buf, MAXBUFLEN);
             if (waiting != 0) {
                if (buf[0] != '#') {
                    // not initial HB
                    printf("Waiting for incoming UDP message.\n");
                    continue;
                }
                iTotalMsg = 0;
                pktSize = 0;
                interval = 0;
                sscanf(buf, "#%d#%d#%d#%d", &iTotalMsg, &pktSize, &interval, &ulcount);
                printf("Received No.%d heart beat: totalmsg: %d, pktSize: %d"
                        ", interval: %d\n", ulcount, iTotalMsg, pktSize, interval);
                memset(content, '*', pktSize);
                tv.tv_sec = 0;
                tv.tv_usec = interval;
                waiting = 0;
                icount = 0;
             } else {
                sscanf(buf, "#%d#%d#%d#%d", &iTotalMsg, &pktSize, &interval, &ulcount);
                printf("Received No.%d heart beat: totalmsg: %d, pktSize: %d"
                        ", interval: %d\n", ulcount, iTotalMsg, pktSize, interval);
                memset(content, '*', pktSize);
                tv.tv_sec = 0;
                tv.tv_usec = interval;
                waiting = 0;
                icount = 0;
             }
        }
    }


}
