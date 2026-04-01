# ============================================================
# COMPUTER NETWORKS - LAB 03 : SOCKET PROGRAMMING
# Complete Reference File - All Tasks Combined
# ============================================================

import socket
import threading
import os
import struct

# ============================================================
# SECTION 1: BASIC SOCKET UTILITIES
# ============================================================

def section1_basic_utilities():
    """
    Covers:
    - Getting your own hostname and IP
    - Getting IP of any website
    - Reverse lookup (IP to hostname)
    - Getting service name from port number
    """

    # --- 1a: Get your own hostname and IP ---
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)
    print("Your hostname:", hostname)
    print("Your IP:", ip)

    # --- 1b: Get IP of any website ---
    sites = ["www.google.com", "www.facebook.com"]
    for site in sites:
        ip = socket.gethostbyname(site)
        print(f"Hostname: {site} | IP: {ip}")

    # --- 1c: Reverse lookup - IP to hostname ---
    # Returns a tuple: (hostname, alias_list, ip_list)
    result = socket.gethostbyaddr("8.8.8.8")
    print("Reverse lookup:", result)
    # Output: ('dns.google', [], ['8.8.8.8'])

    # --- 1d: Get service name from port number ---
    print(socket.getservbyport(80, 'tcp'))   # http
    print(socket.getservbyport(25, 'tcp'))   # smtp
    print(socket.getservbyport(53, 'udp'))   # domain


# ============================================================
# SECTION 2: PORT SCANNER
# ============================================================

def section2_port_scanner():
    """
    Scans ports 50-499 on a target host.
    Uses connect_ex() which returns 0 if port is open,
    non-zero if closed - without throwing exceptions.
    """

    import time
    start = time.time()

    target = input("Enter hostname to scan: ")
    target_ip = socket.gethostbyname(target)
    print("Scanning:", target_ip)

    for port in range(50, 500):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # connect_ex returns 0 = open, non-zero = closed
        # use connect_ex not connect() because connect() throws
        # exception on closed ports and crashes the loop
        result = s.connect_ex((target_ip, port))

        if result == 0:
            print(f"Port {port}: OPEN")

        s.close()  # always close after each attempt

    print("Time taken:", round(time.time() - start, 2), "seconds")


# ============================================================
# SECTION 3: SIMPLE CLIENT-SERVER CHAT WITH FILE TRANSFER
# (Single client only)
# ============================================================

# ------- TASK 3: SERVER -------
def task3_server():
    """
    Simple server that handles ONE client.
    Client can send:
      - Text messages (prefix: MSG|)
      - Files        (prefix: FILE|filename|filedata)

    Key concepts:
    - bind() attaches socket to address and port
    - listen() starts accepting connection queue
    - accept() BLOCKS until client connects, returns (conn, addr)
    - recv() receives bytes, decode() converts to string
    - send() sends bytes, encode() converts string to bytes
    """

    server_socket = socket.socket()
    server_socket.bind(("localhost", 9998))
    server_socket.listen(1)     # only 1 client at a time
    print(">> Server waiting for client...")

    # accept() blocks here until a client connects
    # conn = socket to talk to THIS client
    # addr = client's IP and port
    conn, addr = server_socket.accept()
    print(">> Client connected:", addr)

    while True:
        # receive everything in one recv call
        msg = conn.recv(4096).decode()

        if not msg:
            break

        # --- MESSAGE BRANCH ---
        if msg.startswith("MSG|"):
            text = msg[4:]      # strip "MSG|" prefix (4 chars)
            print("Client:", text)

            if text.lower() == "exit":
                print(">> Client left")
                break

            reply = input("Reply: ")
            conn.send(reply.encode())

            if reply.lower() == "exit":
                print(">> Server closed chat")
                break

        # --- FILE BRANCH ---
        elif msg.startswith("FILE|"):
            # split on | max 2 times to protect file content
            # "FILE|notes.txt|file content here" 
            # → ["FILE", "notes.txt", "file content here"]
            parts = msg.split("|", 2)
            filename = parts[1]
            # encode back to bytes using latin1
            # latin1 maps bytes 0-255 one-to-one, no data loss
            file_data = parts[2].encode("latin1")

            with open("received_" + filename, "wb") as f:
                f.write(file_data)

            print(">> File saved as: received_" + filename)

            reply = input("Reply: ")
            conn.send(reply.encode())

            if reply.lower() == "exit":
                print(">> Server closed connection")
                break

    conn.close()
    server_socket.close()
    print(">> Server shut down")


# ------- TASK 3: CLIENT -------
def task3_client():
    """
    Simple client that connects to ONE server.
    Can send messages or files.

    Key concepts:
    - connect() reaches out to server, triggers server's accept()
    - MSG| prefix tells server it's a text message
    - FILE| prefix tells server it's a file
    - latin1 encoding used for file bytes so they can be
      joined with the filename string in one send()
    """

    client_socket = socket.socket()
    client_socket.connect(("localhost", 9998))
    print(">> Connected to server!")

    while True:
        choice = input("Message (M) or File (F): ").strip().lower()

        # --- SEND MESSAGE ---
        if choice == "m":
            text = input("You: ")
            # prefix MSG| so server knows it's a message
            client_socket.send(("MSG|" + text).encode())

            if text.lower() == "exit":
                print(">> You left the chat")
                break

            reply = client_socket.recv(1024).decode()
            print("Server:", reply)

            if reply.lower() == "exit":
                print(">> Server closed chat")
                break

        # --- SEND FILE ---
        elif choice == "f":
            filename = input("Filename: ")

            # read file as binary, decode with latin1 to string
            # so it can be joined with "FILE|filename|" prefix
            with open(filename, "rb") as f:
                file_data = f.read().decode("latin1")

            # send everything in one packet: FILE|name|data
            client_socket.send(
                ("FILE|" + filename + "|" + file_data).encode()
            )
            print(">> File sent")

            reply = client_socket.recv(1024).decode()
            print("Server:", reply)

            if reply.lower() == "exit":
                print(">> Server closed connection")
                break

    client_socket.close()


# ============================================================
# SECTION 4: MULTI-CLIENT CHAT ROOM
# (Multiple clients using threading)
# ============================================================

# ------- TASK 4: SERVER -------
def task4_server():
    """
    Chat room server - handles MULTIPLE clients simultaneously.

    Key concept - Threading:
    - Without threading: server handles client1 forever,
      client2 can never connect
    - With threading: each client gets its own thread running
      simultaneously
    - threading.Thread(target=fn, args=(a,b)).start()
      runs fn(a,b) in background while main loop keeps going

    Broadcast:
    - active_clients list holds every connected socket
    - when one client sends a message, loop all sockets
      and send to everyone EXCEPT the sender
    """

    server = socket.socket()
    server.bind(("localhost", 9997))
    server.listen(10)       # up to 10 clients can queue
    print(">> Chat room started...")

    # shared list - all threads can access this
    active_clients = []

    def handle_client(conn, addr):
        print(">> User joined:", addr)
        active_clients.append(conn)

        while True:
            try:
                msg = conn.recv(1024).decode()

                # client disconnected abruptly
                if not msg or msg.lower() == "exit":
                    print(">> User left:", addr)
                    active_clients.remove(conn)
                    conn.close()
                    break

                print(f"{addr}: {msg}")

                # broadcast to everyone except sender
                for client in active_clients:
                    if client != conn:
                        client.send(f"{addr}: {msg}".encode())

            except:
                # handles crash or sudden disconnect
                if conn in active_clients:
                    active_clients.remove(conn)
                conn.close()
                break

    # main loop - keeps accepting new clients forever
    # each client gets its own thread immediately
    while True:
        conn, addr = server.accept()
        threading.Thread(
            target=handle_client,
            args=(conn, addr)
        ).start()


# ------- TASK 4: CLIENT -------
def task4_client():
    """
    Chat room client.

    Why threading on client side too?
    - Without it: blocked at input(), can't receive messages
    - With it: one thread listens in background,
               main thread handles typing and sending

    daemon=True means the listener thread automatically
    dies when main program exits.
    """

    client = socket.socket()
    client.connect(("localhost", 9997))
    print(">> Connected to chat room")

    # background thread - just listens and prints
    def listen():
        while True:
            try:
                msg = client.recv(1024).decode()
                if msg:
                    print(msg)
            except:
                break

    threading.Thread(target=listen, daemon=True).start()

    # main thread - handles typing and sending
    while True:
        text = input("You: ")
        client.send(text.encode())

        if text.lower() == "exit":
            print(">> You left the chat")
            client.close()
            break


# ============================================================
# SECTION 5: SECURE MULTI-CLIENT CHAT
# (With message and file validation)
# ============================================================

# ------- TASK 5: SERVER -------
def task5_server():
    """
    Secure chat room server with two validations:

    1. Message validation:
       - Check every message for banned words
       - If found: reject and warn sender, don't broadcast
       - If clean: broadcast to all other clients

    2. File validation:
       - Check file extension before accepting
       - If not in allowed list: reject immediately
       - If allowed: receive full file using chunked transfer

    Chunked file transfer:
    - Client sends filename first
    - Then sends filesize as 4 bytes (struct.pack)
    - Then sends file data in 4096-byte chunks
    - Server keeps receiving until received == filesize
    - This works for files of ANY size reliably

    struct.pack/unpack:
    - pack("!I", 5000) converts integer 5000 → 4 bytes
    - unpack("!I", bytes) converts 4 bytes → integer
    - "!I" = network byte order, unsigned int
    """

    server = socket.socket()
    server.bind(("localhost", 9996))
    server.listen(10)
    print(">> Secure chat server started...")

    active_clients = []

    # validation rules
    ALLOWED_EXTENSIONS = [".txt", ".jpg", ".pdf"]
    BANNED_WORDS = ["spam", "hack", "sensitive"]

    def handle_client(conn, addr):
        print(">> User connected:", addr)
        active_clients.append(conn)

        while True:
            try:
                data = conn.recv(1024).decode()

                if not data:
                    continue

                # --- MESSAGE BRANCH ---
                if data.startswith("MSG:"):
                    msg = data[4:]      # strip "MSG:" prefix

                    if msg.lower() == "exit":
                        print(">> User left:", addr)
                        active_clients.remove(conn)
                        conn.close()
                        break

                    # check every banned word against message
                    # any() returns True if at least one word found
                    if any(word in msg.lower() for word in BANNED_WORDS):
                        conn.send(
                            ">> Blocked: inappropriate content".encode()
                        )
                    else:
                        print(f"{addr}: {msg}")
                        for client in active_clients:
                            if client != conn:
                                client.send(
                                    f"{addr}: {msg}".encode()
                                )

                # --- FILE BRANCH ---
                elif data.startswith("FILE:"):
                    filename = data[5:]     # strip "FILE:" prefix

                    # os.path.splitext("notes.txt") → ('notes', '.txt')
                    ext = os.path.splitext(filename)[1]

                    if ext not in ALLOWED_EXTENSIONS:
                        conn.send(
                            ">> Blocked: file type not allowed".encode()
                        )
                        continue    # skip to next iteration

                    # receive file size - always exactly 4 bytes
                    filesize_bytes = conn.recv(4)
                    filesize = struct.unpack("!I", filesize_bytes)[0]

                    # receive file in chunks until we have it all
                    received = 0
                    file_data = b""
                    while received < filesize:
                        # min() prevents reading past end of file
                        chunk = conn.recv(
                            min(4096, filesize - received)
                        )
                        if not chunk:
                            break
                        file_data += chunk
                        received += len(chunk)

                    with open("received_" + filename, "wb") as f:
                        f.write(file_data)

                    print(f">> {addr} sent file: {filename}")

                    for client in active_clients:
                        if client != conn:
                            client.send(
                                f">> {addr} sent file: {filename}".encode()
                            )

            except:
                if conn in active_clients:
                    active_clients.remove(conn)
                conn.close()
                break

    while True:
        conn, addr = server.accept()
        threading.Thread(
            target=handle_client,
            args=(conn, addr)
        ).start()


# ------- TASK 5: CLIENT -------
def task5_client():
    """
    Secure chat client.
    Sends messages with MSG: prefix.
    Sends files in 3 steps:
      Step 1: filename with FILE: prefix
      Step 2: filesize as 4 bytes using struct.pack
      Step 3: file content in 4096-byte chunks
    """

    client = socket.socket()
    client.connect(("localhost", 9996))
    print(">> Connected to secure chat server")

    # background listener thread
    def receive():
        while True:
            try:
                msg = client.recv(1024).decode()
                if msg:
                    print(msg)
            except:
                break

    threading.Thread(target=receive, daemon=True).start()

    # main send loop
    while True:
        choice = input("Message (M) or File (F): ").strip().lower()

        # --- SEND MESSAGE ---
        if choice == "m":
            msg = input("You: ")
            client.send(f"MSG:{msg}".encode())

            if msg.lower() == "exit":
                print(">> Disconnected")
                client.close()
                break

        # --- SEND FILE ---
        elif choice == "f":
            filename = input("Filename: ")

            if not os.path.exists(filename):
                print(">> File not found")
                continue

            filesize = os.path.getsize(filename)

            # step 1: send filename with FILE: prefix
            client.send(
                f"FILE:{os.path.basename(filename)}".encode()
            )

            # step 2: send filesize as exactly 4 bytes
            # server uses this to know when to stop receiving
            client.send(struct.pack("!I", filesize))

            # step 3: send file content in chunks
            with open(filename, "rb") as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    client.send(chunk)

            print(">> File sent successfully")


# ============================================================
# QUICK REFERENCE - SOCKET METHODS SUMMARY
# ============================================================
#
# CREATING A SOCKET:
#   s = socket.socket()
#   → defaults to AF_INET (IPv4) + SOCK_STREAM (TCP)
#
# SERVER METHODS (in order):
#   s.bind((host, port))     attach socket to address
#   s.listen(backlog)        start accepting queue
#   conn, addr = s.accept()  BLOCKS until client connects
#
# CLIENT METHODS:
#   s.connect((host, port))        connect to server
#   s.connect_ex((host, port))     connect, returns 0 if open
#
# BOTH SIDES:
#   s.send(data.encode())          send bytes
#   s.recv(1024).decode()          receive bytes, convert to str
#   s.close()                      always close when done
#
# UTILITY FUNCTIONS:
#   socket.gethostname()           your machine's hostname
#   socket.gethostbyname(host)     hostname → IP
#   socket.gethostbyaddr(ip)       IP → (hostname, [], [ip])
#   socket.getservbyport(port,     port number → service name
#                        proto)
#
# TCP vs UDP:
#   SOCK_STREAM = TCP  reliable, ordered, connection-based
#   SOCK_DGRAM  = UDP  fast, connectionless, no guarantee
#
# ============================================================


# ============================================================
# RUN WHATEVER YOU NEED:
# Comment out what you don't need, uncomment what you do.
# ============================================================

if __name__ == "__main__":

    # --- SECTION 1: Basic utilities ---
    # section1_basic_utilities()

    # --- SECTION 2: Port scanner ---
    # section2_port_scanner()

    # --- TASK 3: Single client chat ---
    # task3_server()    # run this in terminal 1
    # task3_client()    # run this in terminal 2

    # --- TASK 4: Multi-client chat room ---
    # task4_server()    # run this in terminal 1
    # task4_client()    # run this in terminal 2, 3, 4

    # --- TASK 5: Secure multi-client chat ---
    # task5_server()    # run this in terminal 1
    # task5_client()    # run this in terminal 2, 3, 4

    pass
