#include <sys/socket.h>

#ifndef MOONSKYSOCKET_H_
#define MOONSKYSOCKET_H_


typedef struct _server {
    int sockfd;
    struct sockaddr mySockaddr;
    socklen_t addrlen;
} server;

void *get_in_addr(struct sockaddr *sa);

int getUDPSocket(char *ip, char *port, server *myServer);
int sendUDPMessage(server *myServer, char *message);
int listenOnUDPSocket(char *port);
int recvUDPMessage(server *remoteServer, char *buf, int bufSize);
#endif /*MOONSKYSOCKET_H_*/
