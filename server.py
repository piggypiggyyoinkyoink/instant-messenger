import socket, threading
from threading import Thread, Lock

global maxMessagesDict

def commands(data, cid):
    if (x:=data.decode().split(" "))[0] == "/setmaxmessages":
        try:
            new_max = int(x[1])
            lock.acquire()
            maxMessagesDict[cid] = new_max
            lock.release()
            msg = f"Max messages for client {cid} set to {new_max}"
            print(msg)
            return msg
        except:
            msg = "Invalid command format. Use /setmaxmessages <number>"
            print(msg)
            return msg
    else:return "Invalid command"



def tcp_server_thread(tcp_socket, lock):
    while True:
        # accept connections from outside
        (clientsocket, address) = tcp_socket.accept()
        print(address)
        try:
            thread = Thread(target=tcp_client_thread, args=(clientsocket, address, lock))
            thread.start()
        except:
            print("Error: unable to start thread")
            clientsocket.close()



def udp_server_thread(udp_socket, lock):
    ids = {}
    while True:
        # receive data from client (data, addr)
        data, addr = udp_socket.recvfrom(5000)
        if data.decode().split(":")[0] == "ID" and len(data.decode().split(":")) == 2 and (cid:=(data.decode().split(":")[1])).isnumeric():
            print("DICT", maxMessagesDict)
            print('Client ID is {}'.format(data.decode().split(":")[1]))
            if not(cid in maxMessagesDict.keys()):
                lock.acquire()
                maxMessagesDict[cid] = 5
                lock.release()
            ids[addr] = cid
            udp_socket.sendto(data, addr)
        else:
            try:
                cid = ids[addr]
                print('connection from', cid)
                print('received {!r}'.format(data.decode()))
                if data.decode()[0] == "/":
                    udp_socket.sendto(commands(data, cid).encode(), addr)
                    continue
                if maxMessagesDict[cid] <= 0:
                    msg = f"Max messages reached, ignoring message from client {cid}"
                    print(msg)
                    udp_socket.sendto(msg.encode(), addr)
                    continue
                if data:
                    lock.acquire()
                    maxMessagesDict[cid] -= 1
                    lock.release()
                    print('sending data back to the client')
                    udp_socket.sendto(data, addr)
                else:
                    print('no data from', cid)
            except:
                print("No ID for this address, ignoring message")
                continue
            


def tcp_client_thread(clientsocket, address, lock):
    try:
        print('connection from', address)
        # Receive the data in small chunks and retransmit it
        data = clientsocket.recv(5)
        if data.decode().split(":")[0] == "ID" and len(data.decode().split(":")) == 2 and (cid:=(data.decode().split(":")[1])).isnumeric():
            print("DICT", maxMessagesDict)
            print('Client ID is {}'.format(data.decode().split(":")[1]))
            if not(cid in maxMessagesDict.keys()):
                lock.acquire()
                maxMessagesDict[cid] = 5
                lock.release()
            clientsocket.sendall(data)

            while True:
                data = clientsocket.recv(5000)
                print("DINGUS",maxMessagesDict[cid])
                if data.decode()[0] == "/":
                    clientsocket.sendall(commands(data, cid).encode())
                    continue
        
                if maxMessagesDict[cid] <= 0:
                    msg = f"Max messages reached for client {cid}, closing connection"
                    print(msg)
                    clientsocket.sendall(msg.encode())
                    break
                
                print('received {!r}'.format(data.decode()))
                if data:
                    lock.acquire()
                    maxMessagesDict[cid] -= 1
                    lock.release()
                    print('sending data back to the client')
                    clientsocket.sendall(data)
                else:
                    print('no data from', address)
                    break
        else:
            print("No ID received, closing connection")
            clientsocket.close()
            return

    finally:
        # Clean up the connection
        clientsocket.close()

def a(thread_tcp, thread_udp):
    thread_tcp.daemon = True
    thread_udp.daemon = True
    thread_tcp.start()
    thread_udp.start()
    input()
    return


lock = Lock()
# create TCP socket
tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp_socket.bind((socket.gethostname(), 42000))
tcp_socket.listen(5)
maxMessagesDict = {}
thread_tcp = Thread(target=tcp_server_thread, args=(tcp_socket,lock))

#create UDP socket
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_socket.bind((socket.gethostname(), 43000))
thread_udp = Thread(target=udp_server_thread, args=(udp_socket,lock))

t = Thread(target=a, args=(thread_tcp, thread_udp))
t.start()    