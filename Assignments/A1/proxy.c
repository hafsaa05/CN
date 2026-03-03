#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h> // For close()
#define PORT 4455

int main(int argc, char *argv[])
{
    int serverSocket, newSocket;
    struct sockaddr_in serverAddr, newAddr;

    socklen_t addr_size;
    char buffer[1024];

    serverSocket = socket(PF_INET, SOCK_STREAM, 0); // SOCK_STREAM defines TCP communication
    printf("[+]Server socket created successfully.\n");

    memset(&serverAddr, '\0', sizeof(serverAddr));       // Initialize the server address structure
    serverAddr.sin_family = AF_INET;                     // IPv4 address family
    serverAddr.sin_port = htons(PORT);                   // Set the port number (convert to network byte order)
    serverAddr.sin_addr.s_addr = inet_addr("127.0.0.1"); // Set the server IP address (localhost in this case)

    bind(serverSocket, (struct sockaddr *)&serverAddr, sizeof(serverAddr)); // Bind the socket to the specified IP and port
    printf("[+]Bind to port %d\n", PORT);

    listen(serverSocket, 5); // Listen for incoming connections (max 5 pending connections)
    printf("[+]Listening for incoming connections...\n");

    addr_size = sizeof(newAddr);
    newSocket = accept(serverSocket, (struct sockaddr *)&newAddr, &addr_size); // Accept an incoming connection and create a new socket for communication
    printf("[+] Client connected.\n");

    memset(buffer, 0, sizeof(buffer));
    int bytesReceived = recv(newSocket, buffer, sizeof(buffer) - 1, 0);

    if (bytesReceived > 0)
    {
        buffer[bytesReceived] = '\0'; // Null terminate safely
        printf("\nHTTP Request has recieved\n");
        printf("%s\n", buffer);
    }

    close(newSocket);
    close(serverSocket);

    return 0;
}
