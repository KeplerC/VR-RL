#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <signal.h>
#include <time.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/time.h>
#include <pthread.h>
#include <errno.h>
#include <string.h>
#include "moonskySocket.h"

#define MAXBUFLEN 11760

pid_t dump(char *dump_argv[]);

int main(int argc, char **argv) {
    if (argc != 8) {
        printf("Usage: %s <Server IP> <Server Port> <TotalPkt> <ulPktSize> <PktSize>"
                " <Interval> <Heart beat interval>\n",
                argv[0]);
        return EXIT_FAILURE;
    }
    //printf("**************************************************************\n");
    for (int i = 0; i < argc; i++) {
        //printf("argv[%d]: %s\n", i, argv[i]);
    }
    //printf("**************************************************************\n");


    setenv("TZ", "EST", 0);

    // char interface_name[32] = "rmnet_data0"; // used for Nexus6 and Nexus6P
    // char interface_name[32] = "rmnet0"; // used for Samsung S5
    struct timeval curtv;
    struct tm* ptm;
    char time_string[64];
    gettimeofday(&curtv, NULL);
    ptm = localtime(&curtv.tv_sec);
    strftime(time_string, sizeof(time_string), "%Y-%m-%d_%H-%M-%S", ptm);
    //printf("Cur time: %s\n", time_string);

    // char dump_name[128] = {0};
    // sprintf(dump_name, "/sdcard/UdpSaturator/trace/%s_%s_UdpSaturator.pcap", argv[7], time_string);
    // char *dump_argv[] = {"/system/bin/tcpdump", "-w", dump_name, "-i", interface_name, "udp", "src", "port", "9999", NULL};
    // int pid_tcpdump = dump(dump_argv);



    sleep(1);

    server *remoteServer = (server*)malloc(sizeof(server));
    getUDPSocket(argv[1], argv[2], remoteServer);

    
    int iTotalMsg = atoi(argv[3]);
    int pktSize = atoi(argv[4]);
    int ulpktSize = atoi(argv[5]);
    int interval = atoi(argv[6]);
    int intervalHB = atoi(argv[7]);

    char bufHB[ulpktSize];
    memset(bufHB, '*', ulpktSize);
    bufHB[ulpktSize] = '\0';

    char temp[10];
    sprintf(temp, "#%d#%d#%d#%d", iTotalMsg, pktSize, interval, 1);
    strncpy(bufHB, temp, strlen(temp)); // initial HB

    sendUDPMessage(remoteServer, bufHB);
    struct timeval timestamp;
    gettimeofday(&timestamp,NULL);
    unsigned long time_in_micros = 1000000 * timestamp.tv_sec + timestamp.tv_usec;
    //printf("***Starting in %lu ***\n", time_in_micros);

    char *input;
    input = (char*)malloc(sizeof(*input) * 128);
    fd_set readfds;
    fd_set tempReadfds;
    FD_ZERO(&readfds);
    FD_SET(0, &readfds);
    FD_SET(remoteServer->sockfd, &readfds);
    struct timeval tv;
    tv.tv_sec = 0;
    tv.tv_usec = intervalHB;
    

    char content[MAXBUFLEN];
    int fdMax = remoteServer->sockfd;

    int receivedFirstUDP = -1;
    int pcount = 2;

    int counter = 0;
    // printf("2**************************************************************\n");
    for(;;)
    {
        tempReadfds = readfds;
        int rv = select(fdMax+1, &tempReadfds, NULL, NULL, &tv);
        if (rv == 0)
        {
            // tv timeout
            //printf("***Sending*******************************************\n");
            char temp[10];
            sprintf(temp, "#%d#%d#%d#%d", iTotalMsg, pktSize, interval, pcount);
            strncpy(bufHB, temp, strlen(temp));
            /*
            if (EXIT_SUCCESS != sendUDPMessage(remoteServer, bufHB)) {
                printf("sendUDPMessage failed\n");
            } else {
                printf("NO.%d Heartbeat sent.\n", pcount);
            }
            */
            pcount ++;
        gettimeofday(&timestamp,NULL);
            unsigned long time_in_micros_end = 1000000 * timestamp.tv_sec + timestamp.tv_usec;
            //printf("Sending time: %lu with delay %lu \n", time_in_micros_end, time_in_micros_end - time_in_micros);
            printf("S, %lu, %lu \n", time_in_micros_end, time_in_micros_end - time_in_micros);
            time_in_micros = time_in_micros_end;
            tv.tv_sec = 0;
            tv.tv_usec = intervalHB;
            if (pcount == iTotalMsg) {
                tv.tv_sec = 3600;
            }
        }
        else if (FD_ISSET(0, &tempReadfds))
        {
            //printf("***Exiting*******************************************\n");
            fgets(input, 128, stdin);
            free(input);
            close(remoteServer->sockfd);
            free(remoteServer);
            sleep(3);
            // kill(pid_tcpdump, SIGTERM);

            return(EXIT_SUCCESS);
        }
        else {
            // coming msg from remoteserver
            // printf("***Receiving*****************************************\n");
            counter += 1;
            int rt = recvUDPMessage(remoteServer, content, MAXBUFLEN);
            //printf("Recv pkt from remoteServer, length: %d, ", rt);
            char showbuf[20];
            showbuf[19] = '\0';
            strncpy(showbuf, content, 19);
            int numPkt;
            sscanf(showbuf, "#%d", &numPkt);

            //printf("pkt: [%d],", numPkt);
            // if (numPkt == iTotalMsg) {
            gettimeofday(&timestamp,NULL);
            unsigned long time_in_micros_end = 1000000 * timestamp.tv_sec + timestamp.tv_usec;
            //printf("time: %lu, delay: %lu, length: %d \n", time_in_micros_end, time_in_micros_end - time_in_micros, rt);
            printf("R, %lu, %lu, %d\n", time_in_micros_end, time_in_micros_end - time_in_micros, rt);
            time_in_micros = time_in_micros_end;
            // }
            //     close(remoteServer->sockfd);
            //     free(remoteServer);
            //     sleep(3);
            //     // kill(pid_tcpdump, SIGTERM);
            //     return(EXIT_FAILURE);
            //     fclose(fptr);
            // }
        if(counter >= iTotalMsg){
          //printf("***Exiting*******************************************\n");
          free(input);
          close(remoteServer->sockfd);
          free(remoteServer);
          exit(0);
        }
        }
    }
}

pid_t dump(char *dump_argv[]) {
    pid_t pid;
    int i = 0;
    pid = fork();
    if (pid > 0) {
        return pid;
    } else if (pid == 0) {
        // child process
        printf("-----------------------\nCalling tcpdump ");
        printf("uid: %d\n", getuid());
        printf("execv /system/bin/tcpdump ");
        while (dump_argv[i] != NULL) {
            printf("%s ", dump_argv[i]);
            i++;
        }
        printf("\n-----------------------\n");
        //execv("/usr/sbin/tcpdump", dump_argv);
        if (execv("/system/bin/tcpdump", dump_argv) == -1) {
            printf ("execv failed, errno: %s\n", strerror(errno));
        }
        exit(0);
    } else {
        printf("fork failed\n");
    }
    return pid;
}