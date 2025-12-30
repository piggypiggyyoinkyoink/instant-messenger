import socket, time, sys, os
from threading import Thread, Lock

os.system("color") #enables colours and effects in cmd

#console colours:
global RED; RED = "\x1b[91m"
global LIGHTRED; LIGHTRED = "\x1b[31m"
global GREEN; GREEN = "\x1b[32m"
global LIGHTGREEN; LIGHTGREEN = "\x1b[92m"
global YELLOW; YELLOW = "\x1b[93m"
global LIGHTYELLOW; LIGHTYELLOW = "\x1b[33m"
global LIGHTBLUE; LIGHTBLUE = "\x1b[34m"
global MAGENTA; MAGENTA = "\x1b[95m"
global CYAN; CYAN = "\x1b[96m"
global RESET; RESET = "\x1b[0m"

#console effects:
global PREVLINE; PREVLINE = "\033[F"
global CLEARRIGHT; CLEARRIGHT = "\033[K"
#currently unused:
global BOLD; BOLD = "\x1b[1m"
global ENDBOLD; ENDBOLD = "\x1b[21m"
global UNDERLINE; UNDERLINE = "\x1b[4m"
global ENDUNDERLINE; ENDUNDERLINE = "\x1b[24m"

#protocol message codes
#message format: code⠀source_username⠀dest_user⠀payload
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
    3  : "PING",
    4  : "FILE",
    404: "NOTFOUND",
    41 : "FILELIST",
    5  : "UDPRESEND",
    67 : "BAD",
    69 : "GOOD",
    9  : "DISCONNECT"
}
#global server and broadcast identifiers (consts)
global SERVER; SERVER = "$S_SERVER"
global BROADCAST; BROADCAST = "$S_BROADCAST"
#global status identifiers
global WAITING; WAITING = 0
global GOOD; GOOD = 1
global BAD; BAD = 2
#global protocol identifiers
global TCP; TCP = 1
global UDP; UDP = 2
#global vars for current recipient, mode and status
global recipient
global mode
global status
global protocol
#global list storing joined groups
global groups; groups = []

#initialise values for global vars
recipient = SERVER
mode = "chat"
status = WAITING
protocol = UDP

lock = Lock()


def form_message(code, source_user, dest_user, payload):
    return bytes(f"{message_codes[code]}⠀{source_user}⠀{dest_user}⠀{payload}", "utf-8")

def unpack_message(data:bytes):
    try:
        decoded = data.decode()
        parts = decoded.split("⠀")
        code = int(parts[0])
        source_user = parts[1]
        dest_user = parts[2]
        payload = parts[3]
        return code, source_user, dest_user, payload
    except:
        return None, None, None, None

def send_tcp(tcp_sock, message):
    if type(message) is not bytes:
        lock.release()
        raise Exception()
    lock.acquire()
    if message_codes[unpack_message(message)[0]] == "PING":
        tcp_sock.sendall(message)
        lock.release()
        return
    # Send data
    global status
    status = WAITING
    #print(YELLOW + 'sending {!r}'.format(message.decode("utf-8")))
    tcp_sock.sendall(message)
    t1 = time.time()
    while status == WAITING:
        time.sleep(0.1)
        if time.time() - t1 > 50:
            print(RED + PREVLINE+"Timeout waiting for response" + CLEARRIGHT)
            break
    lock.release()
    if status == GOOD:
        if message_codes[unpack_message(message)[0]] != "PING":
            #print(GREEN + PREVLINE+"Message sent successfully" + CLEARRIGHT)
            pass
        return 1
    else:
        if message_codes[unpack_message(message)[0]] != "PING":
            print(RED + PREVLINE+"Message failed to send" + CLEARRIGHT)
        return None



def send_udp(udp_sock:socket.socket, server_address, msg):
    try:
        # Send data
        udp_sock.sendto(msg, server_address)
        c, s, d, fname = unpack_message(msg)
        notfound = False
        # Receive response
        while True:
            #discard garbage packets from previous downloads
            try:
                data, server = udp_sock.recvfrom(5000)
            except socket.timeout:break
            try:
                code, source_user, dest_user, message = unpack_message(data)
                if code == message_codes["NOTFOUND"]:
                    notfound = True
                if code == message_codes["FILE"] and message.split(",")[0] == fname:
                    break
            except:pass
        if code == message_codes["FILE"] and message.split(",")[0] == fname:
            file_name,file_size = message.split(",")
            file_path = os.path.join(os.getcwd(), username, file_name)
            if not os.path.exists(f"{username}"):
                os.makedirs(f"{username}")
            file_size = int(file_size)
            num_packets = (file_size // 4000) + (1 if file_size % 4000 != 0 else 0)
            print(PREVLINE + YELLOW+f"Downloading file: {file_name} ({file_size} B)")
            remaining = file_size
            packets = {}
            for i in range(num_packets):
                packets[i] = None
            #t1 = time.time()
            try:
                for i in range(num_packets):
                    try:
                        data, server = udp_sock.recvfrom(5000)
                    except socket.timeout:pass
                    if data:
                        file_contents = data[5:]
                        sequence_number = int(data[:5].decode("utf-8"))
                        packets[sequence_number] = file_contents
                        # if not file_contents:
                        #     raise Exception("Connection lost during file transfer")
                        #f.write(file_contents)
                        remaining -= len(file_contents)
                with open(file_path, "wb") as f:
                    for i in range(num_packets):
                        while packets[i] is None:
                            #request resend
                            udp_sock.sendto(form_message("UDPRESEND", username, SERVER, str(i)), server_address)
                            try:
                                data, server = udp_sock.recvfrom(5000)
                            except socket.timeout:pass
                            if data:
                                file_contents = data[5:]
                                sequence_number = int(data[:5].decode("utf-8"))
                                packets[sequence_number] = file_contents
                                if sequence_number == i:
                                    packets[i] = file_contents
                        f.write(packets[i])
                udp_sock.sendto(form_message("GOOD", username, SERVER, f"File {file_name} downloaded successfully"), server_address)
                

                print(GREEN + PREVLINE+ f"File {file_name} downloaded successfully: ({file_size} B)"+ CLEARRIGHT)
            except:
                print(RED + PREVLINE+ f"Error receiving file {file_name}"+ CLEARRIGHT)
                return
        elif notfound:
            print(RED + PREVLINE+ f"File {fname} does not exist on server"+ CLEARRIGHT)
    except:
        print(RED + PREVLINE+ f"Error during UDP file download"+ CLEARRIGHT)
    finally:
        print_prompt()
        return



def print_prompt():
    if mode == "groupchat":
        print(LIGHTGREEN + f"[{recipient}]" + " me:  ", end="", flush=True)
    elif recipient != BROADCAST:    
        print(CYAN + "me -> " + recipient + ":  ", end="",flush=True)
    else:
        print(MAGENTA + "[BROADCAST]" + " me:  ", end="",flush=True)

def client_receive_thread(id, tcp_server_address, udp_server_address):
    global status
    global groups
    tcp_sock = None
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(YELLOW + 'Connecting to {} port {}'.format(*tcp_server_address))
    try:
        tcp_sock.connect(tcp_server_address)
    except:
        print(RED + PREVLINE + "Failed to connect to server" + CLEARRIGHT)
        print(RESET)
        return
    rec_thread = Thread(target=each_client_thread, args=(id, tcp_sock))
    rec_thread.daemon = True
    rec_thread.start()
        
    while True:
        try:
            data = tcp_sock.recv(5000)
        except:
            print(RED + PREVLINE + "Connection lost" + CLEARRIGHT)
            print(YELLOW + "Exited instant messenger")
            print(RESET)
            try:
                tcp_sock.close()
                tcp_sock = None
            except:pass
            
            return
        if data:
            code, source_user, dest_user, message = unpack_message(data)
            if message_codes[code] != "PING" and source_user != SERVER:
                if dest_user == BROADCAST:
                    # incoming message is a broadcast
                    print("")
                    print(MAGENTA + PREVLINE + f"[BROADCAST] {source_user}:  {message}" + CLEARRIGHT)
                elif dest_user == username:
                    # incoming message is a unicast
                    print("")
                    print(LIGHTBLUE + PREVLINE +f"{source_user} -> me:  {message}" + CLEARRIGHT)
                else:
                    # incoming message is a group message
                    print("")
                    print(LIGHTGREEN + PREVLINE +f"[{dest_user}] {source_user}:  {message}" + CLEARRIGHT)

                print_prompt()
            if source_user == SERVER:
                if code == message_codes["GOOD"]:
                    status = GOOD
                elif code == message_codes["BAD"]:
                    status = BAD
                    print(RED + f"[SERVER]:  {message}\n")
                elif code == message_codes["NOTFOUND"]:
                    status = BAD
                    print(RED + f"[SERVER]:  {message}")
                    print_prompt()
                elif code == message_codes["MESSAGE"] or code == message_codes["GROUP_MESSAGE"]:
                    # incoming message is a server broadcast (join/leave message)
                    print("")
                    print(LIGHTRED + PREVLINE + f"[SERVER]:  {message}" + CLEARRIGHT)
                elif code == message_codes["GROUP_LIST"]:
                    # incoming message is a list of groups the user has joined
                    if message == "":
                        groups = []
                    else:
                        groups = message.split(",")
                    # print("")
                    # print(LIGHTYELLOW + PREVLINE + f"[SERVER]:  You have joined groups: {', '.join(groups) if groups else 'None'}" + CLEARRIGHT)
                elif code == message_codes["FILE"]:
                    # incoming message is a signal for the beginning of a file transfer
                    file_name,file_size = message.split(",")
                    file_size = int(file_size)
                    print("")
                    print(LIGHTYELLOW + PREVLINE + f"[SERVER]:  Downloading file: {file_name} ({file_size} B)" + CLEARRIGHT)
                    remaining = file_size
                    try:
                        if not os.path.exists(f"{id}"):
                            os.makedirs(f"{id}")
                        file_name2 = os.path.join(f"{id}", file_name)
                        with open(file_name2, "wb") as f:
                            while remaining > 0:
                                file_contents = tcp_sock.recv(min(4096, remaining))
                                if not file_contents:
                                    raise Exception("Connection lost during file transfer")
                                f.write(file_contents)
                                remaining -= len(file_contents)

                        print(GREEN + PREVLINE +f"File {file_name} downloaded successfully: ({file_size} B)"+ CLEARRIGHT)
                    except:
                        print(RED + PREVLINE +f"[SERVER]:  Error receiving file {file_name} \n"+ CLEARRIGHT)
                        break
                    print_prompt()
                elif code == message_codes["FILELIST"]:
                    # incoming message is a list of files on the server
                    files = message.split(",") if message != "" else []
                    if files == []:
                        print(RED + PREVLINE + f"[SERVER]:  No files available on server." + CLEARRIGHT)
                    else:
                        print(LIGHTYELLOW + PREVLINE + f"[SERVER]:  Files available on server:" + CLEARRIGHT)
                        for file in files:
                            file_name, file_size = file.split(":")
                            print(LIGHTYELLOW + f" - {file_name} ({file_size} B)")
                    print_prompt()
                elif code == message_codes["DISCONNECT"]:
                    print(YELLOW + "Exited instant messenger")
                    print(RESET)
                    time.sleep(0.1)
                    return
                if code == message_codes["MESSAGE"]:
                    print_prompt()

        else:
            print(RED + "Connection closed by server")
            tcp_sock.close()
            print(YELLOW + "Exited instant messenger")
            print(RESET)
            time.sleep(0.1)
            return

def each_client_thread(id, tcp_sock=None):
    global mode
    global recipient
    global groups
    
    #protocol = TCP
    #udp_sock = None
    message = "⠀"
    recipient = SERVER
    mode = "chat"
        
    try:
        #send id
        res = send_tcp(tcp_sock, form_message("ID", str(id), SERVER, str(id)))
        if res is None:
            raise Exception(RED + "Failed to setup connection")
        print(GREEN +"\n"+ PREVLINE +" - /chat <username> : enter chat mode with a user."+ CLEARRIGHT+"\n - /gc <groupname> : enter group chat mode. \n - /broadcast : enter broadcast mode.\n - /join <groupname> : join/create a group. \n - /leave <groupname> : leave a group.\n - /listfiles : list all files in the SharedFiles folder. \n - /dl <filename.ext> : download a file. \n - /kill : quit the messenger."+ CLEARRIGHT)
    except: 
        print(RED + "Failed to setup connection")
        tcp_sock.close()
        return
    while message != "/kill":
        if tcp_sock is None:
            return
        output_prompt = True

        if message.startswith("/broadcast"):
            #broadcast mode - to everyone
            mode = "chat"
            recipient = BROADCAST
            print(YELLOW + PREVLINE + "Entering broadcast mode"+ CLEARRIGHT)
        elif message.startswith("/chat "):
            #unicast chat mode (to a specific user)
            mode = "chat"
            if message[len("/chat "):] == username:
                print(RED+ PREVLINE +"Cannot chat with yourself"+ CLEARRIGHT)
            else:
                recipient = message[len("/chat "):]
                print(YELLOW + PREVLINE +f"Chatting with {recipient}"+ CLEARRIGHT)
        elif message.startswith("/gc "):
            #group chat mode - multicast
            #only if user has joined the group
            if message[len("/gc "):] not in groups or groups == []:
                print(RED + PREVLINE +f"You are not a member of {message[len('/gc '):]}"+ CLEARRIGHT)
            else:
                mode = "groupchat"
                recipient = message[len("/gc "):]
                print(YELLOW + PREVLINE +f"Group chatting in {recipient}"+ CLEARRIGHT)
        elif message.startswith("/join "):
            #join a group
            group_name = message[len("/join "):]
            if group_name in groups:
                print(RED + PREVLINE +f"Already a member of {group_name}"+ CLEARRIGHT)
                output_prompt = True
            else:
                try:
                    send_tcp(tcp_sock, form_message("JOIN", str(id), SERVER, group_name))
                    groups.append(group_name)
                    # joining a group results in a server message that gets displayed by the receive thread which automatically 
                    # updates the "me -> recipient" prompt so set output_prompt to false to avoid duplicate prompt
                    output_prompt = False
                except:
                    #print(RED + "Connection lost")
                    tcp_sock.close()
                    tcp_sock = None
        elif message.startswith("/leave "):
            #leave a group
            group_name = message[len("/leave "):]
            if recipient == group_name:
                # if currently chatting in the group we just left, return to chat mode so can no longer message the left group
                recipient = SERVER
                mode = "chat"
                # this overwrites the group chat prompt
                print(YELLOW + PREVLINE + "Returning to chat mode"+ CLEARRIGHT)
                # now write chat mode prompt
                output_prompt = True
            try:
                # leaving a group results in a server message that gets displayed by the receive thread which automatically 
                # updates the "me -> recipient" prompt so set output_prompt to false to avoid duplicate prompt
                if group_name in groups:
                    output_prompt = False
                    send_tcp(tcp_sock, form_message("LEAVE", str(id), SERVER, group_name))
                    groups.remove(group_name)
                else:
                    print(RED + PREVLINE +f"Not a member of {group_name}"+ CLEARRIGHT)
            except:
                #print(RED + "Connection lost")
                tcp_sock.close()
                tcp_sock = None
        elif message.startswith("/dl "):
            #download a file from server
            file_name = message[len("/dl "):]
            try:
                if protocol == TCP:
                    send_tcp(tcp_sock, form_message("FILE", str(id), SERVER, file_name))
                elif protocol == UDP:
                    send_udp(udp_sock, udp_server_address, form_message("FILE", str(id), SERVER, file_name))
                output_prompt = False
                # receiving the file is handled by the receive thread
            except Exception as e:
                if protocol == TCP:
                    tcp_sock.close()
                    tcp_sock = None
                else:
                    raise e
                
        elif message.startswith("/listfiles"):
            #request list of files from server
            try:
                send_tcp(tcp_sock, form_message("FILELIST", str(id), SERVER, ""))
                output_prompt = False
                # receiving the file list is handled by the receive thread
            except:
                tcp_sock.close()
                tcp_sock = None
            
        
        else:
            try:
                if mode == "chat":
                    send_tcp(tcp_sock, form_message("MESSAGE", str(id), recipient, message))
                elif mode == "groupchat": 
                    send_tcp(tcp_sock, form_message("GROUP_MESSAGE", str(id), recipient, message))
            except:
                #print(RED + "Connection lost")
                tcp_sock.close()
                tcp_sock = None
        if output_prompt:
            print_prompt()
        message = input()
    try:
        send_tcp(tcp_sock, form_message("DISCONNECT", str(id), SERVER, ""))
    except:
        try:
            tcp_sock.close()
        except:return
    return



# Create a TCP/IP socket
try:
    args = sys.argv[1:]
    username, hostname, port = (args[0], args[1], int(args[2]))
except:
    print(RED + "Invalid command line arguments. Using default values.")
    username, hostname, port = ("default", socket.gethostname(), 42000)
print(username, hostname, port)
# Connect the socket to the port where the server is listening
tcp_server_address = (hostname, port)
#print(YELLOW + 'connecting to {} port {}'.format(*tcp_server_address))
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_sock.settimeout(0.1)
udp_server_address = (hostname, port)
thread = Thread(target=client_receive_thread, args=(username, tcp_server_address, udp_server_address))
thread.start()
