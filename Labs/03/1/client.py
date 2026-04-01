import socket

client_socket = socket.socket()
client_socket.connect(("localhost", 9998))
print("Connected to server!")

while True:
    choice = input("Message (M) or File (F) or Exit (E): ").strip().lower()

    if choice == "m":
        text = input("You: ")
        client_socket.send(("MSG|" + text).encode())
        if text.lower() == "exit":
            break
        reply = client_socket.recv(1024).decode()
        print("Server:", reply)
        if reply.lower() == "exit":
            break

    elif choice == "f":
        filename = input("Filename: ")
        with open(filename, "rb") as f:
            file_data = f.read().decode("latin1")
        client_socket.send(("FILE|" + filename + "|" + file_data).encode())
        reply = client_socket.recv(1024).decode()
        print("Server:", reply)

    elif choice == "e":
        client_socket.send("MSG|exit".encode())
        break

client_socket.close()
