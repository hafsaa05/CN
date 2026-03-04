import socket
import os
import sys

BUFSIZE     = 4096
MAXCHILDREN = 100  # max 100 child processes at a time, dont want it going crazy

def main():
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <port>", file=sys.stderr)
        sys.exit(1)

    listenport = int(sys.argv[1])

    # socket setup from Beej's guide - socket() then bind() then listen() then accept()
    listenfd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # SO_REUSEADDR so we dont get "address already in use" error when restarting proxy
    listenfd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    listenfd.bind(("", listenport))  # listen on all interfaces not just localhost

    listenfd.listen(10)

    print(f"PROXY STARTED ON PORT {listenport}")

    nchildren = 0  # counting active children so we know when to stop forking

    # keep waiting for new browser connections forever
    while True:

        # clean up any finished child processes before accepting new connection
        try:
            while True:
                pid, _ = os.waitpid(-1, os.WNOHANG)
                if pid == 0:
                    break
                nchildren -= 1
        except ChildProcessError:
            pass

        connfd, clientaddr = listenfd.accept()

        print("NEW REQUEST RECEIVED")

        # if too many clients already connected just drop this one
        if nchildren >= MAXCHILDREN:
            print("SERVER BUSY, CONNECTION DROPPED", file=sys.stderr)
            connfd.send(b"HTTP/1.0 503 Service Unavailable\r\n\r\n")
            connfd.close()
            continue

        # fork a child to handle this client so parent can go back to accepting
        pid = os.fork()

        if pid == 0:
            # child process starts here
            listenfd.close()  # child doesnt need the listening socket at all

            # read browser request in format GET http://host/path HTTP/1.0\r\n headers\r\n\r\n
            data = connfd.recv(BUFSIZE - 1)

            if not data:
                connfd.close()
                os._exit(0)

            buf = data.decode("utf-8", errors="replace")
            print(f"REQUEST CONTENTS:\n{buf}\n")

            # split the first line into method, url, version
            firstline = buf.split("\r\n")[0]
            parts     = firstline.split(" ")

            # if any of these are missing the request is malformed
            if len(parts) < 3:
                connfd.send(b"HTTP/1.0 400 Bad Request\r\n\r\n")
                connfd.close()
                os._exit(0)

            method  = parts[0]
            url     = parts[1]
            version = parts[2].strip()  # trim spaces if any

            # browsers send HTTP/1.1 but we accept both 1.0 and 1.1 from client side
            # we always forward to server as HTTP/1.0 since thats what assignment wants
            if version not in ("HTTP/1.0", "HTTP/1.1"):
                print(f"BAD HTTP VERSION: {version}")
                connfd.send(b"HTTP/1.0 400 Bad Request\r\n\r\n")
                connfd.close()
                os._exit(0)

            # only GET is allowed, anything else send 501
            if method != "GET":
                print(f"METHOD NOT SUPPORTED: {method}, SENDING 501")
                connfd.send(b"HTTP/1.0 501 Not Implemented\r\n\r\n")
                connfd.close()
                os._exit(0)

            # URL has to be absolute like http://example.com/path (RFC 1945 section 5.1.2)
            if not url.startswith("http://"):
                connfd.send(b"HTTP/1.0 400 Bad Request\r\n\r\nURL must be absolute (http://...)\r\n")
                connfd.close()
                os._exit(0)

            # now parse out hostname, port and path from the URL
            remoteport = 80  # default HTTP port

            hoststart = url[7:]               # skip past "http://"
            slash     = hoststart.find("/")   # find where path starts

            if slash != -1:
                hostonly = hoststart[:slash]
                path     = hoststart[slash:]
            else:
                # no slash so no path given, default to "/"
                hostonly = hoststart
                path     = "/"

            # check if port number is specified in the URL like example.com:8080
            if ":" in hostonly:
                colon      = hostonly.find(":")
                hostname   = hostonly[:colon]
                remoteport = int(hostonly[colon+1:]) or 80  # remove port from hostname string
            else:
                hostname = hostonly

            if not hostname:
                connfd.send(b"HTTP/1.0 400 Bad Request\r\n\r\n")
                connfd.close()
                os._exit(0)

            print(f"CONNECTING TO HOST: {hostname}  PORT: {remoteport}  PATH: {path}")

            # use getaddrinfo to resolve hostname, Beej says use this instead of old gethostbyname
            try:
                res = socket.getaddrinfo(hostname, remoteport, socket.AF_INET, socket.SOCK_STREAM)
            except socket.gaierror:
                print(f"COULD NOT RESOLVE HOST: {hostname}")
                connfd.send(b"HTTP/1.0 502 Bad Gateway\r\n\r\n")
                connfd.close()
                os._exit(0)

            # open socket to the real server
            serverfd = socket.socket(res[0][0], res[0][1], res[0][2])

            try:
                serverfd.connect(res[0][4])
            except Exception:
                connfd.send(b"HTTP/1.0 502 Bad Gateway\r\n\r\n")
                serverfd.close()
                connfd.close()
                os._exit(0)

            # send request to real server as HTTP/1.0 with Connection: close
            # Connection: close tells server to close after response so recv loop knows when to stop
            req = f"GET {path} HTTP/1.0\r\nHost: {hostname}\r\nConnection: close\r\n\r\n"
            serverfd.send(req.encode())

            # read response from server and send it directly back to browser
            # no modification just pass through as is
            while True:
                chunk = serverfd.recv(BUFSIZE)
                if not chunk:
                    break
                connfd.send(chunk)

            serverfd.close()
            connfd.close()
            print("RESPONSE SENT TO CLIENT, CONNECTION CLOSED")
            os._exit(0)  # child done

        else:
            # parent process - just increment count and go back to accept()
            nchildren += 1
            connfd.close()  # parent doesnt need this socket, child has it

    listenfd.close()

if __name__ == "__main__":
    main()
