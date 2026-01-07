import socket, sys, os
from threading import Thread, Lock
from dotenv import load_dotenv

#protocol message codes
global MESSAGE_CODES
MESSAGE_CODES = {
    "ID" : 0,
    "MESSAGE" : 1,
    "GROUP_MESSAGE":11,
    "JOIN" : 21,
    "LEAVE" : 22,
    "GROUP_LIST" : 23,
    "FILE" : 4,
    "NOTFOUND" : 404,
    "FILELIST" : 41,
    "UDPRESEND" : 5,
    "BAD" : 67,
    "GOOD" : 69,
    "DISCONNECT" : 9,
    0  : "ID",
    1  : "MESSAGE",
    11 : "GROUP_MESSAGE",
    21 : "JOIN",
    22 : "LEAVE",
    23 : "GROUP_LIST",
    4  : "FILE",
    404: "NOTFOUND",
    41 : "FILELIST",
    5  : "UDPRESEND",
    67 : "BAD",
    69 : "GOOD",
    9  : "DISCONNECT"
}
#dict to store all connected users and their sockets
global user_dict; user_dict = {}
#format:  user_dict[username] = [socket1, socket2,...]

#dict to store locks for each client socket to prevent two processes sending to same socket simultaneously
global client_lock_dict; client_lock_dict = {}
#format:  client_lock_dict[addr] = Lock()

#dict to store all groups and their members
global group_dict; group_dict = {}
#format:  group_dict[group_name] = [username1, username2,...]

#global server and broadcast identifiers (consts)
global SERVER; SERVER = "$S_SERVER"
global BROADCAST; BROADCAST = "$S_BROADCAST"

#message format:  code⠀source_username⠀dest_user⠀payload

#read SERVER_SHARED_FILES from environment variable or use default (./SharedFiles)
load_dotenv()
SERVER_SHARED_FILES = os.environ.get("SERVER_SHARED_FILES", os.path.join(os.getcwd(), "SharedFiles"))



def form_message(code, source_user, dest_user, payload):
    #form message
    #message format: code⠀source_username⠀dest_user⠀payload
    #separator is U+2800 unicode character
    return bytes(f"{MESSAGE_CODES[code]}⠀{source_user}⠀{dest_user}⠀{payload}", "utf-8")



def unpack_message(data:bytes):
    #decode message
    #message format: code⠀source_username⠀dest_user⠀payload
    #separator is U+2800 unicode character
    try:
        decoded = data.decode()
        parts = decoded.split("⠀")  #blank unicode character used as separator to prevent conflicts with normal text
        code = int(parts[0])
        source_user = parts[1]
        dest_user = parts[2]
        payload = parts[3]
        return code, source_user, dest_user, payload
    except:
        return None, None, None, None



def tcp_server_thread(tcp_socket, user_dict_lock, group_dict_lock):
    #tcp server thread
    while True:
        # accept connections from outside
        (clientsocket, address) = tcp_socket.accept()
        try:
            #start new thread for each new client
            thread = Thread(target=tcp_client_thread, args=(clientsocket, address, user_dict_lock, group_dict_lock))
            thread.start()
        except:
            print("Error: unable to start thread")
            clientsocket.close()



def send_file_udp(udp_socket:socket.socket, addr, cid, file_name, buf):
    #check file exists
    if os.path.exists(file_path:=(os.path.join(SERVER_SHARED_FILES, file_name))):
        file_size = os.path.getsize(file_path)
        try:
            #collect dictionary of packets (seq_num: packet_data)
            with open(file_path, "rb") as f:
                #send file name and size
                print("sending file name and size")
                udp_socket.sendto(form_message("FILE", SERVER, cid, file_name + ","+str(file_size)), addr)
                #send file contents
                packets = {}
                i = 0
                while file_contents:= f.read(4000):
                    #send file in packets of 4000 bytes with 5 digit sequence number
                    packets[i] = file_contents
                    packet = bytes(f"{('00000'+str(i))[-5:]}", "utf-8") + file_contents
                    i+=1
                    udp_socket.sendto(packet, addr)
            received = False
            while received == False:
                try:
                    udp_socket.settimeout(5.0)
                    try:
                        #intercept response (GOOD, BAD, UDPRESEND)
                        data, addr = udp_socket.recvfrom(5000)
                    except socket.timeout:break
                    code, source_user, dest_user, message = unpack_message(data)
                    if code == MESSAGE_CODES["GOOD"]:
                        #file successfully downloaded by client
                        print("good")
                        #mark as received and break loop
                        received = True
                        break
                    if code == MESSAGE_CODES["BAD"]:
                        #file download failed
                        print("bad")
                        break
                    elif code == MESSAGE_CODES["UDPRESEND"]:
                        #resend requested packet
                        seq_num = int(message)
                        print("resending packet",seq_num,"for",file_name)
                        packet = bytes(f"{('00000'+str(seq_num))[-5:]}", "utf-8") + packets[seq_num]
                        udp_socket.sendto(packet, addr)
                    elif code == MESSAGE_CODES["FILE"]:
                        #another file download request received - buffer it for later processing
                        if source_user != cid:
                            buf.append((data, addr))
                except Exception as e:
                    print(e)
                    #resend all packets
                    print("resending all packets for",file_name)
                    for seq_num in packets:
                        print("resending packet",seq_num,"for",file_name)
                        packet = bytes(f"{('00000'+str(seq_num))[-5:]}", "utf-8") + packets[seq_num]
                        udp_socket.sendto(packet, addr)
            if received == False:
                #if timeout, something is wrong 
                #do not send response as client is not listening - could affect future requests
                print("bad")
        except:
            print("bad")
    else:
        print(f"File {file_name} does not exist on server")
        udp_socket.sendto(form_message("NOTFOUND", SERVER, cid, f"{file_name}"), addr)
    return buf



def udp_server_thread(udp_socket:socket.socket):
    #udp server thread
    udp_socket.setblocking(False)
    buf = []
    while True:
        udp_socket.settimeout(0.5)
        #check buffer for any pending messages first
        if buf:
            data, addr = buf.pop(0)
        else:
            # receive data from client (data, addr)
            try:
                data, addr = udp_socket.recvfrom(5000)
            except socket.timeout:
                continue
        
        code, source_user, dest_user, message = unpack_message(data)
        cid = source_user
        print("UDP message code:", code, "from", source_user, "to", dest_user)
        #ignore anything that isnt a file download request
        if code == MESSAGE_CODES["FILE"]:
            #file downloading
            buf = send_file_udp(udp_socket, addr, cid, message, buf)        



def initialise_client(clientsocket:socket.socket, client_lock:Lock, cid, user_dict_lock:Lock, group_dict_lock:Lock):
    user_dict_lock.acquire()
    #add socket to user_dict
    try:
        user_dict[cid].append(clientsocket)
    except:
        user_dict[cid] = [clientsocket]
    user_dict_lock.release()
    #send GOOD response to client
    response = form_message("GOOD", SERVER, cid, "ID accepted")
    client_lock.acquire()
    clientsocket.sendall(response)
    client_lock.release()

    #broadcast join message
    broadcast_message(form_message("MESSAGE", SERVER, BROADCAST, f"{cid} has joined"), SERVER, user_dict_lock)

    #send list of groups the user is a member of
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
    return



def unicast_message(clientsocket:socket.socket, source_user, dest_user, data, client_lock:Lock, user_dict_lock:Lock):
    #get all active sockets corresponding to dest_user
    user_dict_lock.acquire()
    recipients = user_dict.get(dest_user, [])
    user_dict_lock.release()
    if not recipients:
        #dest_user offline - send BAD response to source_user
        client_lock.acquire()
        clientsocket.sendall(form_message("BAD", SERVER, source_user, "Recipient is offline"))
        client_lock.release()
        return
    #send to each active socket of dest_user
    for recipient in recipients:
        recipient_lock = client_lock_dict.get(recipient, None)
        recipient_lock.acquire()
        try:
            recipient.sendall(data)
        except:
            client_lock.acquire()
            clientsocket.sendall(form_message("BAD", SERVER, source_user, "Recipient is offline"))
            client_lock.release()
        finally:
            recipient_lock.release()
    return


            
def broadcast_message(message, source_user, user_dict_lock:Lock):
    #send broadcast message to all users except source_user
    #get all active sockets except source_user
    user_dict_lock.acquire()
    recipients = []
    try:
        for user in user_dict:
            if user != source_user:
                recipients.extend(user_dict[user])
    finally:
        user_dict_lock.release()
    #send message to all recipients
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
    #send multicast message to all members of group except source_user
    code, source_user, dest_user, payload = unpack_message(message)
    group_dict_lock.acquire()
    try:
        #get all members of group
        members = group_dict.get(group_name, [])
    finally:
        group_dict_lock.release()
    if not members:
        return
    user_dict_lock.acquire()
    recipients = []
    try:
        #get all active sockets corresponding to group members except source_user
        for member in members:
            if member != source_user:
                recipients.extend(user_dict.get(member, []))
    finally:
        user_dict_lock.release()
    
    if recipients:
        #send message to all recipients
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



def join_group(cid, group_name, group_dict_lock:Lock):
    #add user to group dict
    if cid not in group_dict.get(group_name, []):
        group_dict_lock.acquire()
        try:
            group_dict[group_name].append(cid)
        except:
            group_dict[group_name] = [cid]
        finally:
            group_dict_lock.release()
        #send message to group members signifying user has joined
        print(cid,"has joined group", group_name)
        groupcast_message(form_message("MESSAGE", SERVER, group_name, f"{cid} has joined group {group_name}"), group_name, user_dict_lock, group_dict_lock)
    return
                    


def send_file_tcp(clientsocket:socket.socket, client_lock:Lock, cid, file_name):
    #check if file exists
    if os.path.exists(file_path:=(os.path.join(SERVER_SHARED_FILES, file_name))):
        file_size = os.path.getsize(file_path)
        client_lock.acquire()
        try:
            with open(file_path, "rb") as f:
                #send file name and size
                clientsocket.sendall(form_message("FILE", SERVER, cid, file_name+","+str(file_size)))
                #send file contents
                while file_contents:= f.read(4096):
                    clientsocket.sendall(file_contents)
                #send GOOD message
                clientsocket.sendall(form_message("GOOD", SERVER, cid, f"File {file_name} sent successfully"))
        except:
            clientsocket.sendall(form_message("BAD", SERVER, cid, f"Error sending file {file_name}"))
        finally:
            client_lock.release()
    else:
        #file not found - send NOTFOUND message
        client_lock.acquire()
        try:
            clientsocket.sendall(form_message("NOTFOUND", SERVER, cid, f"File {file_name} does not exist on server"))
        finally:
            client_lock.release()
    return



def send_file_list(clientsocket:socket.socket, client_lock:Lock, cid):
    try:
        #get list of files in SERVER_SHARED_FILES
        files = os.listdir(SERVER_SHARED_FILES)
        for i in range(len(files)):
            file = files[i]
            #get size of each file and append to filename with colon separator
            file_path = os.path.join(SERVER_SHARED_FILES, file)
            file_size = os.path.getsize(file_path)
            files[i]+=":"+str(file_size)
        #stringify file list with comma separator ready for sending to client
        files_str = ",".join(files)
        #send stringified file list to client
        client_lock.acquire()
        try:
            clientsocket.sendall(form_message("FILELIST", SERVER, cid, files_str))
            #send GOOD response too to update the status on client side
            clientsocket.sendall(form_message("GOOD", SERVER, cid, "File list sent successfully"))
        finally:
            client_lock.release()
    except:
        client_lock.acquire()
        try:
            #send BAD response if fails to update status on client side
            clientsocket.sendall(form_message("BAD", SERVER, cid, "Error retrieving file list"))
        finally:
            client_lock.release()
    return



def disconnect_client(clientsocket:socket.socket, cid, client_lock:Lock, user_dict_lock:Lock):
    client_lock.acquire()
    #send disconnect confirmation to client so it can exit cleanly
    try:
        clientsocket.sendall(form_message("DISCONNECT", SERVER, cid, "Disconnected successfully"))
    finally:
        client_lock.release()
    #broadcast leave message to all other clients
    broadcast_message(form_message("MESSAGE", SERVER, BROADCAST, f"{cid} has left"), SERVER, user_dict_lock)
    #remove disconnected socket from user_dict
    user_dict_lock.acquire()
    user_dict[cid].remove(clientsocket)
    user_dict_lock.release()
    clientsocket.close()



def tcp_client_thread(clientsocket:socket.socket, address, user_dict_lock:Lock, group_dict_lock:Lock):
    #thread for each connected client
    global client_lock_dict
    global user_dict
    client_lock_dict[clientsocket] = Lock()
    client_lock = client_lock_dict[clientsocket]
    cid = None
    try:
        print("Incoming connection from", address)
        try:
            data = clientsocket.recv(9000)
        except:
            raise Exception()
        code, source_user, dest_user, message = unpack_message(data)
        #read initial identifier message cntaining username
        if code == MESSAGE_CODES["ID"] and source_user is not None:
            print(f"username: {source_user}")
            cid = source_user
            #initialise client
            initialise_client(clientsocket, client_lock, cid, user_dict_lock, group_dict_lock)
            #main loop for receiving messages from client
            while True:
                try:
                    data = clientsocket.recv(9000) #what if its over 9000?
                except:
                    #Receving failed - client is disconnected
                    print(cid,"disconnected")
                    #broadcast leave message
                    broadcast_message(form_message("MESSAGE", SERVER, BROADCAST, f"{cid} has left"), SERVER, user_dict_lock)
                    #remove disconnected socket from dictionary
                    user_dict_lock.acquire()
                    user_dict[cid].remove(clientsocket)
                    user_dict_lock.release()
                    #exit thread
                    return
                try:
                    #read message
                    code, source_user, dest_user, message = unpack_message(data)
                    
                    #JOIN: add user to group and notify group members
                    if code == MESSAGE_CODES["JOIN"]:
                        join_group(cid, message, group_dict_lock)

                    #LEAVE: remove user from group and notify group members
                    elif code == MESSAGE_CODES["LEAVE"]:
                        #remove user from group
                        group_name = message
                        group_dict_lock.acquire()
                        try:
                            group_dict[group_name].remove(source_user)
                            print(source_user,"has left group", group_name)
                        finally:
                            group_dict_lock.release()
                        #send message to group members signifying user has left
                        groupcast_message(form_message("MESSAGE", SERVER, group_name, f"{source_user} has left group {group_name}"), group_name, user_dict_lock, group_dict_lock)
                        client_lock.acquire()
                        try:
                            #send message to source_user confirming they have left the group
                            clientsocket.sendall(form_message("MESSAGE", SERVER, cid, f"Left group {group_name}"))
                        except:pass
                        finally:
                            client_lock.release()

                    #GROUP_MESSAGE: retransmit message to all group members except source_user
                    elif code == MESSAGE_CODES["GROUP_MESSAGE"]:
                        #retransmit to all active sockets corresponding to group members except source_user
                        group_name = dest_user
                        groupcast_message(form_message("MESSAGE", source_user, group_name, message), group_name, user_dict_lock, group_dict_lock)

                    #FILE: handle TCP file download request
                    elif code == MESSAGE_CODES["FILE"]:
                        send_file_tcp(clientsocket, client_lock, cid, message)

                    #FILELIST: send list of files in SERVER_SHARED_FILES
                    elif code == MESSAGE_CODES["FILELIST"]:
                        send_file_list(clientsocket, client_lock, cid)
                        
                    #DISCONNECT: handle client disconnection (on /kill)
                    elif code == MESSAGE_CODES["DISCONNECT"]:
                        print(cid,"disconnected")
                        disconnect_client(clientsocket, cid, client_lock, user_dict_lock)
                        return
                    
                    #MESSAGE: broadcast: retransmit message to all other users
                    if code == MESSAGE_CODES["MESSAGE"] and dest_user == BROADCAST:
                        #retransmit to all clients except source_user
                        broadcast_message(data, source_user, user_dict_lock)
                    
                    #MESSAGE: unicast: retransmit message to dest_user
                    elif code == MESSAGE_CODES["MESSAGE"] and dest_user != SERVER:
                        unicast_message(clientsocket, source_user, dest_user, data, client_lock, user_dict_lock)
                        
                    print("Received " + message + " from " + cid)
                    if data:
                        #send GOOD message to client confirming message was sent
                        print("Sending response to", cid)
                        response = form_message("GOOD", SERVER, cid, "Message sent successfully")
                        client_lock.acquire()
                        clientsocket.sendall(response)
                        client_lock.release()
                    else:
                        print("No data from", cid)
                        break
                except:
                    #exception occurs -> send BAD response to client
                    client_lock.acquire()
                    clientsocket.sendall(form_message("BAD", SERVER, cid, "Error processing message"))
                    client_lock.release()
                    continue
        else:
            #no identifier message received - invalid connection. Close socket
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
        finally:
            user_dict_lock.release()
        client_lock_dict.pop(clientsocket)
        clientsocket.close()



def main_thread(thread_tcp, thread_udp):
    #start TCP and UDP server threads
    thread_tcp.daemon = True
    thread_udp.daemon = True
    thread_tcp.start()
    thread_udp.start()
    #kill server on keyboard input - prevents infinite hang
    input()
    return



#program start
#define locks
user_dict_lock = Lock()
group_dict_lock = Lock()
#get port number from command line argument or use default 42000
try:
    args = sys.argv[1:]
    port = (int(args[0]))
except:
    print("No port number provided, using default 42000")
    port = 42000
# create TCP socket and server thread
tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp_socket.bind((socket.gethostbyname(socket.gethostname()), port))
print("Server running on", socket.gethostbyname(socket.gethostname()), "port", port)
tcp_socket.listen(5)
thread_tcp = Thread(target=tcp_server_thread, args=(tcp_socket,user_dict_lock, group_dict_lock))

#create UDP socket and server thread
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_socket.bind((socket.gethostbyname(socket.gethostname()), port))
thread_udp = Thread(target=udp_server_thread, args=(udp_socket,))

#start main thread
t = Thread(target=main_thread, args=(thread_tcp, thread_udp))
t.start()    