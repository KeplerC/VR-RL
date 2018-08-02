#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <signal.h>
#include <time.h>
#include <strings.h>
#include <arpa/inet.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netdb.h>
#include <errno.h>
#include <unistd.h>
#include <limits.h>
#include "moonskySocket.h"

int getUDPSocket(char *ip, char *port, server *myServer)
{
    struct addrinfo hints, *servinfo, *p;
    int rv;
    memset(&hints, 0, sizeof(hints));
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_DGRAM;

    if ((rv = getaddrinfo(ip, port, &hints, &servinfo)) != 0)
    {
        printf("Error: getaddrinfo failed\n");
        return EXIT_FAILURE;
    }

    for(p = servinfo; p != NULL; p = p->ai_next)
    {
        if ((myServer->sockfd = socket(p->ai_family, p->ai_socktype, p->ai_protocol)) == -1)
        {
            continue;
        }
        break;
    }

    if (p == NULL)
    {
        printf("Error: failed to bind socket\n");
        return EXIT_FAILURE;
    }

    myServer->mySockaddr = *(p->ai_addr);
    myServer->addrlen = p->ai_addrlen;
    freeaddrinfo(servinfo);
    //printf ("getUDPSocket: sockfd: %d\n", myServer->sockfd);
    return EXIT_SUCCESS;
}

int sendUDPMessage(server *myServer, char *message)
{
    int byteSent = 0;
    if ((byteSent = sendto(myServer->sockfd, message, strlen(message), 0, &(myServer->mySockaddr), myServer->addrlen)) == -1)
    {
        printf("Error: sendUDPMessage failed\n");
        return EXIT_FAILURE;
    }

    if (byteSent != (int)strlen(message))
    {
        printf("Error: snedUDPMessage not complete\n");
        return EXIT_FAILURE;
    }
    //printf ("sendUDPMessage: input msg length %ld, sent msg length %d\n", strlen(message), byteSent);


    // char clientName[128];
    // char serv[128];
    // int return_getnameinfo = getnameinfo((struct sockaddr*) &myServer->mySockaddr,
    //         (myServer->mySockaddr.sa_family == AF_INET) ?
    //                 sizeof(struct sockaddr_in) : sizeof(struct sockaddr_in6),
    //         clientName, 128, serv, 128,
    //         NI_NUMERICHOST & NI_NUMERICSERV);
    // if (return_getnameinfo != 0) {
    //     printf("getnameinfo() failed: %s\n", gai_strerror(return_getnameinfo));
    // }


    // char _clientIPString[INET6_ADDRSTRLEN];
    // char *clientIPString;
    // inet_ntop(myServer->mySockaddr.sa_family,
    //         (myServer->mySockaddr.sa_family == AF_INET) ?
    //                 (void*) &(((struct sockaddr_in*) &myServer->mySockaddr)->sin_addr) :
    //                 (void*) &(((struct sockaddr_in6*) &myServer->mySockaddr)->sin6_addr),
    //         _clientIPString, sizeof(_clientIPString));
    // if (strncmp(_clientIPString, "::ffff:", strlen("::ffff:")) == 0)
    //     clientIPString = _clientIPString + strlen("::ffff:");
    // else
    //     clientIPString = _clientIPString;

    // printf("Send to %s <%s>: %s\n", "phone", clientIPString,
    //         serv);
    // fflush(stdout);

    return EXIT_SUCCESS;
}

void *get_in_addr(struct sockaddr *sa) {
    if (sa->sa_family == AF_INET) {
        return &(((struct sockaddr_in*)sa)->sin_addr);
    } else {
        return &(((struct sockaddr_in6*)sa)->sin6_addr);
    }
}

int listenOnUDPSocket(char *MYPORT) {
    int sockfd;
    struct addrinfo hints, *servinfo, *p;
    int rv;

    memset(&hints, 0, sizeof hints);
    hints.ai_family = AF_UNSPEC; // set to AF_INET to force IPv4
    hints.ai_socktype = SOCK_DGRAM;
    hints.ai_flags = AI_PASSIVE; // use my IP

    if ((rv = getaddrinfo(NULL, MYPORT, &hints, &servinfo)) != 0) {
        fprintf(stderr, "getaddrinfo: %s\n", gai_strerror(rv));
        return -1;
    }

    // loop through all the results and bind to the first we can
    for(p = servinfo; p != NULL; p = p->ai_next) {
        if ((sockfd = socket(p->ai_family, p->ai_socktype,
                p->ai_protocol)) == -1) {
            perror("listener: socket");
            continue;
        }

        if (bind(sockfd, p->ai_addr, p->ai_addrlen) == -1) {
            close(sockfd);
            perror("listener: bind");
            continue;
        }

        break;
    }

    if (p == NULL) {
        fprintf(stderr, "listener: failed to bind socket\n");
        return -1;
    }

    freeaddrinfo(servinfo);

    return sockfd;
}

int recvUDPMessage(server *remoteServer, char *buf, int bufSize) {
    // int numbytes;
    // struct sockaddr_in their_addr;
    // int addr_len = sizeof(their_addr);
    // bzero(&their_addr, sizeof(their_addr));
    // if ((numbytes = recvfrom(remoteServer->sockfd, buf, bufSize-1, 0,
    //                 (struct sockaddr *)&their_addr, &addr_len)) == -1) {
    //     fprintf(stderr, "recvUDPMessage");
    //     return -1;
    // }
    // buf[bufSize] = '\0';
    // remoteServer->addrlen = addr_len;
    // remoteServer->mySockaddr = *(struct sockaddr *)&their_addr;

    // printf("recv from %s:%d\n", inet_ntoa(their_addr.sin_addr), ntohs(their_addr.sin_port));

    // int rt = sendto(remoteServer->sockfd, buf, bufSize-1, 0, (struct sockaddr *)&their_addr, addr_len);

    // printf ("send one single packet to phone, length: %d\n", rt);


    // return numbytes;
    int numbytes;
    struct sockaddr_storage their_addr;
    socklen_t addr_len = sizeof(their_addr);
    bzero(&their_addr, sizeof(their_addr));
    if ((numbytes = recvfrom(remoteServer->sockfd, buf, bufSize-1, 0,
                    (struct sockaddr *)&their_addr, &addr_len)) == -1) {
        fprintf(stderr, "recvUDPMessage");
        return -1;
    }
    buf[bufSize] = '\0';
    remoteServer->addrlen = addr_len;
    remoteServer->mySockaddr = *(struct sockaddr *)&their_addr;
    return numbytes;
}
