import socket, sys
from threading import Thread, Lock

global message_codes
message_codes = {
    "ID" : 0,
    "MESSAGE" : 1,
    "COMMAND" : 2,
    "PING" : 3,
    "QUERY" : 4,
    "BAD" : 67,
    "GOOD" : 69,
    "DISCONNECT" : 9,
    0 : "ID",
    1 : "MESSAGE",
    2 : "COMMAND",
    3 : "PING",
    4 : "QUERY",
    67: "BAD",
    69: "GOOD",
    9 : "DISCONNECT"
}
global user_dict; user_dict = {}
#user_dict[addr] = username
#user_dict[username] = [addr1, addr2,...]
global client_lock_dict; client_lock_dict = {}
#client_lock_dict[addr] = Lock()
global SERVER
SERVER = "$S_SERVER"
global BROADCAST; BROADCAST = "$S_BROADCAST"

#mesage format: code⠀source_username⠀dest_user⠀payload

def commands(data, cid):
    return "Invalid command"

# def check_user_dict():
#     for user in user_dict:
#         for addr in user_dict[user]:
#             print('pinging ', addr)
#             ping = form_message("PING", SERVER, user, "ping")
#             clientsocket.sendall(ping)

def form_message(code, source_user, dest_user, payload):
    return bytes(f"{message_codes[code]}⠀{source_user}⠀{dest_user}⠀{payload}", "utf-8")

def unpack_message(data:bytes):
    try:
        decoded = data.decode()
        print(decoded)
        parts = decoded.split("⠀")
        code = int(parts[0])
        source_user = parts[1]
        dest_user = parts[2]
        payload = parts[3]
        return code, source_user, dest_user, payload
    except:
        return None, None, None, None

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
                if data:
                    print('sending data back to the client')
                    udp_socket.sendto(data, addr)
                else:
                    print('no data from', cid)
            except:
                print("No ID for this address, ignoring message")
                continue
            


def tcp_client_thread(clientsocket, address, user_dict_lock:Lock):
    global client_lock_dict
    client_lock_dict[address] = Lock()
    client_lock = client_lock_dict[address]
    try:
        print('connection from', address)
        # Receive the data in small chunks and retransmit it
        try:
            data = clientsocket.recv(9000)
        except:return
        code, source_user, dest_user, message = unpack_message(data)
        print("CODE:", code)
        print("ID:", source_user)
        if code == message_codes["ID"] and source_user is not None:
            print('Client ID is {}'.format(source_user))
            cid = source_user
            user_dict_lock.acquire()
            #user_dict[address] = cid
            try:
                user_dict[cid].append(address)
            except:
                user_dict[cid] = [address]
            user_dict_lock.release()
            response = form_message("GOOD", SERVER, cid, "ID accepted")
            client_lock.acquire()
            clientsocket.sendall(response)
            client_lock.release()

            while True:
                try:
                    data = clientsocket.recv(9000) #what if its over 9000?
                except:
                    #disconnected - need to broadcast message to all clients 
                    print("disconnected")
                    user_dict[cid].remove(address)
                    return
                print("DINGUS")
                try:
                    code, source_user, dest_user, message = unpack_message(data)
                    if code == message_codes["COMMAND"]:
                        #clientsocket.sendall(commands(data, cid).encode())
                        continue
                    if code == message_codes["MESSAGE"] and dest_user is BROADCAST:
                        #update user dict to check for disconnected ips - send a ping and check for response
                        pass

                    if code == message_codes["MESSAGE"] and dest_user is not SERVER:
                        pass
                    if code == message_codes["PING"]:
                        print("pong")
                        continue
                    print("Received " + message + " from " + cid)
                    if data:
                        print('sending data back to the client')
                        response = form_message("GOOD", SERVER, cid, message)
                        client_lock.acquire()
                        clientsocket.sendall(response)
                        client_lock.release()
                    else:
                        print('no data from', cid)
                        break
                except:
                    client_lock.acquire()
                    clientsocket.sendall(form_message("BAD", SERVER, cid, "Error processing message"))
                    client_lock.release()
                    continue
        else:
            print("No ID received, closing connection")
            client_lock.acquire()
            clientsocket.sendall(form_message("BAD", SERVER, source_user, "No ID received"))
            client_lock.release()
            clientsocket.close()
            return

    finally:
        # Clean up the connection
        user_dict[cid].remove(address)
        client_lock_dict.pop(address)
        clientsocket.close()

def a(thread_tcp, thread_udp):
    thread_tcp.daemon = True
    thread_udp.daemon = True
    thread_tcp.start()
    thread_udp.start()
    input()
    return


user_dict_lock = Lock()
try:
    args = sys.argv[1:]
    port = (int(args[0]))
except:
    print("No port number provided, using default 42000")
    port = 42000
# create TCP socket
tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp_socket.bind((socket.gethostbyname(socket.gethostname()), port))
print("Server running on", socket.gethostbyname(socket.gethostname()), "port", port)
tcp_socket.listen(5)
thread_tcp = Thread(target=tcp_server_thread, args=(tcp_socket,user_dict_lock))

#create UDP socket
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_socket.bind((socket.gethostname(), port+1000))
thread_udp = Thread(target=udp_server_thread, args=(udp_socket,user_dict_lock))

t = Thread(target=a, args=(thread_tcp, thread_udp))
t.start()    