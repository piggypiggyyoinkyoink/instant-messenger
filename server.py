import socket, sys, shutil, os
from threading import Thread, Lock

global message_codes
message_codes = {
    "ID" : 0,
    "MESSAGE" : 1,
    "GROUP_MESSAGE":11,
    "JOIN" : 21,
    "LEAVE" : 22,
    "GROUP_LIST" : 23,
    "PING" : 3,
    "FILE" : 4,
    "BAD" : 67,
    "GOOD" : 69,
    "DISCONNECT" : 9,
    0 : "ID",
    1 : "MESSAGE",
    11: "GROUP_MESSAGE",
    21: "JOIN",
    22: "LEAVE",
    23: "GROUP_LIST",
    3 : "PING",
    4 : "FILE",
    67: "BAD",
    69: "GOOD",
    9 : "DISCONNECT"
}
global user_dict; user_dict = {}
#user_dict[username] = [socket1, socket2,...]
global client_lock_dict; client_lock_dict = {}
#client_lock_dict[addr] = Lock()
global group_dict; group_dict = {}
#group_dict[group_name] = [username1, username2,...]
global SERVER
SERVER = "$S_SERVER"
global BROADCAST; BROADCAST = "$S_BROADCAST"

#mesage format: code⠀source_username⠀dest_user⠀payload

SERVER_SHARED_FILES = "D:\\! CS\\Y2\\Networks and Systems\\instant-messenger\\SharedFiles"


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


def tcp_server_thread(tcp_socket, user_dict_lock, group_dict_lock):
    while True:
        # accept connections from outside
        (clientsocket, address) = tcp_socket.accept()
        print(address)
        try:
            thread = Thread(target=tcp_client_thread, args=(clientsocket, address, user_dict_lock, group_dict_lock))
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
                # if data.decode()[0] == "/":
                #     udp_socket.sendto(commands(data, cid).encode(), addr)
                #     continue
                if data:
                    print('sending data back to the client')
                    udp_socket.sendto(data, addr)
                else:
                    print('no data from', cid)
            except:
                print("No ID for this address, ignoring message")
                continue
            
def broadcast_message(message, source_user, user_dict_lock:Lock):
    user_dict_lock.acquire()
    recipients = []
    try:
        for user in user_dict:
            if user != source_user:
                recipients.extend(user_dict[user])
    finally:
        user_dict_lock.release()
    if recipients:
        for recipient in recipients:
            recipient_lock = client_lock_dict.get(recipient, None)
            recipient_lock.acquire()
            try:
                recipient.sendall(message)
            except:
                #recipient offline - do not throw error here as only one recipient failed
                pass
            finally:
                recipient_lock.release()
    return

def groupcast_message(message, group_name, user_dict_lock:Lock, group_dict_lock:Lock):
    code, source_user, dest_user, payload = unpack_message(message)
    group_dict_lock.acquire()
    try:
        members = group_dict.get(group_name, [])
    finally:
        group_dict_lock.release()
    if not members:
        return
    user_dict_lock.acquire()
    recipients = []
    try:
        for member in members:
            if member != source_user:
                recipients.extend(user_dict.get(member, []))
    finally:
        user_dict_lock.release()
    if recipients:
        for recipient in recipients:
            recipient_lock = client_lock_dict.get(recipient, None)
            recipient_lock.acquire()
            try:
                recipient.sendall(message)
            except:
                #recipient offline - do not throw error here as only one recipient failed
                pass
            finally:
                recipient_lock.release()
    return

def tcp_client_thread(clientsocket:socket.socket, address, user_dict_lock:Lock, group_dict_lock:Lock):
    global client_lock_dict
    global user_dict
    client_lock_dict[clientsocket] = Lock()
    client_lock = client_lock_dict[clientsocket]
    cid = None
    try:
        print('connection from', address)
        try:
            data = clientsocket.recv(9000)
        except:
            raise Exception()
        code, source_user, dest_user, message = unpack_message(data)
        print("CODE:", code)
        print("ID:", source_user)
        if code == message_codes["ID"] and source_user is not None:
            print('Client ID is {}'.format(source_user))
            cid = source_user
            user_dict_lock.acquire()
            try:
                user_dict[cid].append(clientsocket)
            except:
                user_dict[cid] = [clientsocket]
            user_dict_lock.release()
            response = form_message("GOOD", SERVER, cid, "ID accepted")
            client_lock.acquire()
            clientsocket.sendall(response)
            client_lock.release()
            broadcast_message(form_message("MESSAGE", SERVER, BROADCAST, f"{cid} has joined"), SERVER, user_dict_lock)

            group_dict_lock.acquire()
            try:
                groups = [group for group in group_dict if cid in group_dict[group]]
                groups_str = ",".join(groups)
            finally:
                group_dict_lock.release()
            print("groups_str:", groups_str)
            client_lock.acquire()
            clientsocket.sendall(form_message("GROUP_LIST", SERVER, cid, groups_str))
            client_lock.release()
            while True:
                try:
                    data = clientsocket.recv(9000) #what if its over 9000?
                except:
                    #disconnected
                    print("disconnected")
                    #broadcast leave message
                    broadcast_message(form_message("MESSAGE", SERVER, BROADCAST, f"{cid} has left"), SERVER, user_dict_lock)
                    #remove inactive socket from dictionary
                    user_dict_lock.acquire()
                    user_dict[cid].remove(clientsocket)
                    user_dict_lock.release()
                    return
                try:
                    code, source_user, dest_user, message = unpack_message(data)
                    if code == message_codes["JOIN"]:
                        group_name = message
                        if source_user not in group_dict.get(group_name, []):
                            group_dict_lock.acquire()
                            try:
                                group_dict[group_name].append(source_user)
                            except:
                                group_dict[group_name] = [source_user]
                            finally:
                                group_dict_lock.release()
                            groupcast_message(form_message("MESSAGE", SERVER, group_name, f"{source_user} has joined group {group_name}"), group_name, user_dict_lock, group_dict_lock)
                        pass
                    elif code == message_codes["LEAVE"]:
                        group_name = message
                        group_dict_lock.acquire()
                        try:
                            group_dict[group_name].remove(source_user)
                            print("left group", group_name)
                        except:
                            pass
                        finally:
                            group_dict_lock.release()
                        groupcast_message(form_message("MESSAGE", SERVER, group_name, f"{source_user} has left group {group_name}"), group_name, user_dict_lock, group_dict_lock)
                        client_lock.acquire()
                        try:
                            clientsocket.sendall(form_message("MESSAGE", SERVER, cid, f"Left group {group_name}"))
                        except:pass
                        finally:
                            client_lock.release()
                        pass
                    elif code == message_codes["GROUP_MESSAGE"]:
                        group_name = dest_user
                        groupcast_message(form_message("MESSAGE", source_user, group_name, message), group_name, user_dict_lock, group_dict_lock)
                        pass
                    elif code == message_codes["FILE"]:
                        file_name = message
                        if os.path.exists(file_path:=(os.path.join(SERVER_SHARED_FILES, file_name))):
                            file_size = os.path.getsize(file_path)
                            client_lock.acquire()
                            try:
                                with open(file_path, "rb") as f:
                                    clientsocket.sendall(form_message("FILE", SERVER, cid, file_name+","+str(file_size)))
                                    while file_contents:= f.read(4096):
                                        clientsocket.sendall(file_contents)
                                    # outfile = clientsocket.makefile('wb')
                                    # shutil.copyfileobj(f, outfile)
                                    #outfile.flush()
                                    clientsocket.sendall(form_message("GOOD", SERVER, cid, f"File {file_name} sent successfully"))
                            except:
                                clientsocket.sendall(form_message("BAD", SERVER, cid, f"Error sending file {file_name}"))
                            finally:
                                client_lock.release()
                        else:
                            client_lock.acquire()
                            try:
                                clientsocket.sendall(form_message("BAD", SERVER, cid, f"File {file_name} does not exist on server"))
                            finally:
                                client_lock.release()


                    if code == message_codes["MESSAGE"] and dest_user == BROADCAST:
                        #retransmit to all clients except source_user
                        broadcast_message(data, source_user, user_dict_lock)
                        pass

                    elif code == message_codes["MESSAGE"] and dest_user != SERVER:
                        #retransmit to all active sockets corresponding to dest_user
                        user_dict_lock.acquire()
                        recipients = user_dict.get(dest_user, [])
                        user_dict_lock.release()
                        if not recipients:
                            client_lock.acquire()
                            clientsocket.sendall(form_message("BAD", SERVER, cid, "Recipient is offline"))
                            client_lock.release()
                            continue
                        for recipient in recipients:
                            recipient_lock = client_lock_dict.get(recipient, None)
                            recipient_lock.acquire()
                            try:
                                recipient.sendall(data)
                            except:
                                client_lock.acquire()
                                clientsocket.sendall(form_message("BAD", SERVER, cid, "Recipient is offline"))
                                client_lock.release()
                            finally:
                                recipient_lock.release()
                        pass
                    if code == message_codes["PING"]:
                        print("pong")
                        continue
                    print("Received " + message + " from " + cid)
                    if data:
                        print('sending data back to the client')
                        response = form_message("GOOD", SERVER, cid, "Message sent successfully")
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
        user_dict_lock.acquire()
        try:
            user_dict[cid].remove(clientsocket)
        except:pass
        finally:
            user_dict_lock.release()
        client_lock_dict.pop(clientsocket)
        clientsocket.close()

def a(thread_tcp, thread_udp):
    thread_tcp.daemon = True
    thread_udp.daemon = True
    thread_tcp.start()
    thread_udp.start()
    input()
    return


user_dict_lock = Lock()
group_dict_lock = Lock()
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
thread_tcp = Thread(target=tcp_server_thread, args=(tcp_socket,user_dict_lock, group_dict_lock))

#create UDP socket
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_socket.bind((socket.gethostname(), port))
thread_udp = Thread(target=udp_server_thread, args=(udp_socket,user_dict_lock))

t = Thread(target=a, args=(thread_tcp, thread_udp))
t.start()    