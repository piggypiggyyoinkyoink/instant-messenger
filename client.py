import socket, time, sys, os
from threading import Thread, Lock
from colorama import Fore, Back, Style

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
global SERVER; SERVER = "$S_SERVER"
global BROADCAST; BROADCAST = "$S_BROADCAST"
global WAITING; WAITING = 0
global GOOD; GOOD = 1
global BAD; BAD = 2
global recipient; recipient = SERVER
global mode; mode = "chat"
global status
global groups; groups = []
status = WAITING
#mesage format: code⠀source_username⠀dest_user⠀payload
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
    #print(Fore.YELLOW + 'sending {!r}'.format(message.decode("utf-8")))
    tcp_sock.sendall(message)
    t1 = time.time()
    while status == WAITING:
        time.sleep(0.1)
        if time.time() - t1 > 50:
            print(Fore.RED + "\033[F"+"Timeout waiting for response" + "\033[K")
            break
    lock.release()
    if status == GOOD:
        if message_codes[unpack_message(message)[0]] != "PING":
            #print(Fore.GREEN + "\033[F"+"Message sent successfully" + "\033[K")
            pass
        return 1
    else:
        if message_codes[unpack_message(message)[0]] != "PING":
            print(Fore.RED + "\033[F"+"Message failed to send" + "\033[K")
        return None



def send_udp(udp_sock:socket.socket, server_address, message):
    try:
        # Send data
        print('sending {!r}'.format(message))
        udp_sock.sendto(bytes(message, 'utf-8'), server_address)

        # Receive response
        print('waiting to receive')
        data, server = udp_sock.recvfrom(5000)
        print('received {!r}'.format(data.decode("utf-8")))

    finally:
        return



def print_prompt():
    if mode == "groupchat":
        print(Fore.LIGHTGREEN_EX + f"[{recipient}]" + " me:  ", end="", flush=True)
    elif recipient != BROADCAST:    
        print(Fore.CYAN + "me -> " + recipient + ":  ", end="",flush=True)
    else:
        print(Fore.MAGENTA + "[BROADCAST]" + " me:  ", end="",flush=True)

def client_receive_thread(id, tcp_server_address, udp_server_address):
    global status
    global groups
    tcp_sock = None
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(Fore.YELLOW + 'Connecting to {} port {}'.format(*tcp_server_address))
    try:
        tcp_sock.connect(tcp_server_address)
    except:
        print(Fore.RED +f"\033[F"+ "Failed to connect to server" +f"\033[K")
        print(Style.RESET_ALL)
        return
    rec_thread = Thread(target=each_client_thread, args=(id, tcp_server_address, udp_server_address, tcp_sock))
    rec_thread.daemon = True
    rec_thread.start()
        
    while True:
        try:
            data = tcp_sock.recv(5000)
        except:
            print(Fore.RED +f"\033[F"+ "Connection lost" +f"\033[K")
            print(Fore.YELLOW + "Exited instant messenger")
            print(Style.RESET_ALL)
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
                    print(Fore.MAGENTA +f"\033[F"+ f"[BROADCAST] {source_user}:  {message}" + f"\033[K")
                elif dest_user == username:
                    # incoming message is a unicast
                    print("")
                    print(Fore.LIGHTBLUE_EX +f"\033[F"+f"{source_user} -> me:  {message}" + f"\033[K")
                else:
                    # incoming message is a group message
                    print("")
                    print(Fore.LIGHTGREEN_EX +f"\033[F"+f"[{dest_user}] {source_user}:  {message}" + f"\033[K")

                print_prompt()
            if source_user == SERVER:
                if code == message_codes["GOOD"]:
                    status = GOOD
                elif code == message_codes["BAD"]:
                    status = BAD
                    print(Fore.RED + f"[SERVER]:  {message}\n")
                elif code == message_codes["MESSAGE"] or code == message_codes["GROUP_MESSAGE"]:
                    # incoming message is a server broadcast (join/leave message)
                    print("")
                    print(Fore.LIGHTRED_EX +f"\033[F"+ f"[SERVER]:  {message}" + f"\033[K")
                elif code == message_codes["GROUP_LIST"]:
                    # incoming message is a list of groups the user has joined
                    if message == "":
                        groups = []
                    else:
                        groups = message.split(",")
                    # print("")
                    # print(Fore.LIGHTYELLOW_EX +f"\033[F"+ f"[SERVER]:  You have joined groups: {', '.join(groups) if groups else 'None'}" + f"\033[K")
                elif code == message_codes["FILE"]:
                    file_name,file_size = message.split(",")
                    file_size = int(file_size)
                    print("")
                    print(Fore.LIGHTYELLOW_EX +f"\033[F"+ f"[SERVER]:  Downloading file: {file_name} ({file_size} B)" + f"\033[K")
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
                                # infile = tcp_sock.makefile('rb')
                                # shutil.copyfileobj(infile, f)

                        print(Fore.GREEN + f"[SERVER]:  File {file_name} received successfully")
                    except:
                        print(Fore.RED + f"[SERVER]:  Error receiving file {file_name}\n")
                        break
                    print_prompt()
                if code == message_codes["MESSAGE"]:
                    print_prompt()

        else:
            print(Fore.RED + "Connection closed by server")
            tcp_sock.close()
            print(Fore.YELLOW + "Exited instant messenger")
            print(Style.RESET_ALL)
            time.sleep(0.1)
            return

def each_client_thread(id, tcp_server_address, udp_server_address, tcp_sock=None):
    global mode
    global recipient
    global groups
    TCP = 1
    UDP = 2
    #protocol = TCP
    #udp_sock = None
    message = "⠀"
    recipient = SERVER
    mode = "chat"
        
    try:
        #send id
        res = send_tcp(tcp_sock, form_message("ID", str(id), SERVER, str(id)))
        if res is None:
            raise Exception(Fore.RED + "Failed to setup connection")
        print(Fore.GREEN + f"\033[F"+"Connected. Enter /chat <username> to chat and /kill to quit."+f"\033[K")
    except: 
        print(Fore.RED + "Failed to setup connection")
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
            print(Fore.YELLOW + f"\033[F"+ "Entering broadcast mode"+f"\033[K")
        elif message.startswith("/chat "):
            #unicast chat mode (to a specific user)
            mode = "chat"
            if message[len("/chat "):] == username:
                print(Fore.RED + f"\033[F""Cannot chat with yourself"+f"\033[K")
            else:
                recipient = message[len("/chat "):]
                print(Fore.YELLOW + f"\033[F"+f"Chatting with {recipient}"+f"\033[K")
        elif message.startswith("/gc "):
            #group chat mode - multicast
            #only if user has joined the group
            if message[len("/gc "):] not in groups or groups == []:
                print(Fore.RED + f"\033[F"+f"You are not a member of {message[len('/gc '):]}"+f"\033[K")
            else:
                mode = "groupchat"
                recipient = message[len("/gc "):]
                print(Fore.YELLOW + f"\033[F"+f"Group chatting in {recipient}"+f"\033[K")
        elif message.startswith("/join "):
            #join a group
            group_name = message[len("/join "):]
            if group_name in groups:
                print(Fore.RED + f"\033[F"+f"Already a member of {group_name}"+f"\033[K")
                output_prompt = True
            else:
                try:
                    send_tcp(tcp_sock, form_message("JOIN", str(id), SERVER, group_name))
                    groups.append(group_name)
                    # joining a group results in a server message that gets displayed by the receive thread which automatically 
                    # updates the "me -> recipient" prompt so set output_prompt to false to avoid duplicate prompt
                    output_prompt = False
                except:
                    #print(Fore.RED + "Connection lost")
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
                print(Fore.YELLOW + f"\033[F"+ "Returning to chat mode"+f"\033[K")
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
                    print(Fore.RED + f"\033[F"+f"Not a member of {group_name}"+f"\033[K")
            except:
                #print(Fore.RED + "Connection lost")
                tcp_sock.close()
                tcp_sock = None
        elif message.startswith("/dl "):
            #download a file from server
            file_name = message[len("/dl "):]
            try:
                send_tcp(tcp_sock, form_message("FILE", str(id), SERVER, file_name))
                output_prompt = False
                # receiving the file is handled by the receive thread
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
                #print(Fore.RED + "Connection lost")
                tcp_sock.close()
                tcp_sock = None
        if output_prompt:
            print_prompt()
        message = input()
    try:
        tcp_sock.close()
    except:return
    return



# Create a TCP/IP socket
try:
    args = sys.argv[1:]
    username, hostname, port = (args[0], args[1], int(args[2]))
except:
    print(Fore.RED + "Invalid command line arguments. Using default values.")
    username, hostname, port = ("default", socket.gethostname(), 42000)
print(username, hostname, port)
# Connect the socket to the port where the server is listening
tcp_server_address = (hostname, port)
#print(Fore.YELLOW + 'connecting to {} port {}'.format(*tcp_server_address))
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_server_address = (hostname, port)
thread = Thread(target=client_receive_thread, args=(username, tcp_server_address, udp_server_address))
thread.start()
