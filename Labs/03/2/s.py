import socket
import threading

server = socket.socket()
server.bind(("localhost", 9997))
server.listen(10)
print(">> Chat server started...")

active_users = []  # stores every connected client's socket

def client_handler(conn, address):
    print(">> New user joined:", address)
    active_users.append(conn)  # add this client to the room

    while True:
        try:
            message = conn.recv(1024).decode()

            if not message or message.lower() == "exit":
                print(">> User left:", address)
                active_users.remove(conn)
                conn.close()
                break

            print(f"{address}: {message}")

            # broadcast to everyone except sender
            for user in active_users:
                if user != conn:
                    user.send(f"{address}: {message}".encode())

        except:
            if conn in active_users:
                active_users.remove(conn)
            conn.close()
            break

# main loop — keeps accepting new clients forever
while True:
    conn, addr = server.accept()
    threading.Thread(target=client_handler, args=(conn, addr)).start()
