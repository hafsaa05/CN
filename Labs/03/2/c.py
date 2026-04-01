import socket
import threading

client = socket.socket()
client.connect(("localhost", 9997))
print(">> Connected to chat room")

# this thread listens for incoming messages in the background
def listen():
    while True:
        try:
            msg = client.recv(1024).decode()
            if not msg:
                break
            print(msg)
        except:
            break

threading.Thread(target=listen, daemon=True).start()

# main thread handles sending
while True:
    text = input("You: ")
    client.send(text.encode())
    if text.lower() == "exit":
        print(">> You left the chat")
        client.close()
        break
