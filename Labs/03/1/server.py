import socket

server_socket = socket.socket()
server_socket.bind(("localhost", 9998))
server_socket.listen(1)
print(">> Server is running... waiting for client")

conn, addr = server_socket.accept()
print(">> Client connected from:", addr)

while True:
    msg = conn.recv(4096).decode()

    if not msg:
        break

    if msg.startswith("MSG|"):
        text = msg[4:]
        print("Client:", text)
        if text.lower() == "exit":
            print(">> Client exited chat")
            break
        reply = input("Reply: ")
        conn.send(reply.encode())
        if reply.lower() == "exit":
            print(">> Server closed chat")
            break

    elif msg.startswith("FILE|"):
        parts = msg.split("|", 2)
        filename = parts[1]
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
