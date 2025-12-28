import socket, time, sys
from threading import Thread, Lock, Semaphore
from colorama import Fore, Back, Style

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
global SERVER; SERVER = "$S_SERVER"
global BROADCAST; BROADCAST = "$S_BROADCAST"
global WAITING; WAITING = 0
global GOOD; GOOD = 1
global BAD; BAD = 2
global recipient; recipient = SERVER
global lts; lts = 0

global status
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
        if time.time() - t1 > 5:
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


def ping_thread(tcp_sock, username):
    while True:
        time.sleep(10)
        ping = form_message("PING", username, SERVER, "ping")
        try:
            send_tcp(tcp_sock, ping)
        except:
            #print(Fore.RED + "Connection lost")
            tcp_sock.close()
            return


def client_receive_thread(tcp_sock):
    global status
    while True:
        try:
            data = tcp_sock.recv(5000)
        except:
            print(Fore.RED + "Connection lost")
            tcp_sock.close()
            return
        if data:
            code, source_user, dest_user, message = unpack_message(data)
            if message_codes[code] != "PING" and source_user != SERVER:
                print("")
                print(Fore.LIGHTBLUE_EX +f"\033[F"+f"{source_user} -> me:  {message}" + f"\033[K")
                print(Fore.CYAN + "me -> " + source_user + ":  "+ f"\033[K", end='', flush=True)
            if source_user == SERVER:
                if code == message_codes["GOOD"]:
                    status = GOOD
                elif code == message_codes["BAD"]:
                    status = BAD
                    print(Fore.RED + f"[SERVER]: {message}\n")
        else:
            print(Fore.RED + "Connection closed by server")
            tcp_sock.close()
            return

def each_client_thread(id, tcp_server_address, udp_server_address):
    TCP = 1
    UDP = 2
    #protocol = TCP
    tcp_sock = None
    udp_sock = None
    #message = input(Fore.CYAN + "")
    message = "-"
    global recipient
    recipient = SERVER
    while message != "/kill":
        if tcp_sock is None:
            tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print(Fore.YELLOW + 'Connecting to {} port {}'.format(*tcp_server_address))
            try:
                tcp_sock.connect(tcp_server_address)
            except:
                print(Fore.RED + "Failed to connect to server")
                return
            rec_thread = Thread(target=client_receive_thread, args=(tcp_sock,))
            rec_thread.daemon = True
            rec_thread.start()
            
            try:
                #send id
                for i in range(3):
                    # try 3 times
                    res = send_tcp(tcp_sock, form_message("ID", str(id), SERVER, str(id)))
                    if res is not None:
                        break
                if res is None:
                    raise Exception(Fore.RED + "Failed to setup connection")
                p_thread = Thread(target=ping_thread, args=(tcp_sock, id))
                p_thread.daemon = True
                p_thread.start()
                print(Fore.GREEN + "Connected. Enter /chat <username> to chat and /kill to quit.")
            except: 
                print(Fore.RED + "Failed to setup connection")
                tcp_sock.close()
                return
        
        if message.startswith("/broadcast "):
            recipient = BROADCAST
            print(Fore.YELLOW + "Broadcasting message")
            message = message[len("/broadcast "):]
            print(message)
            continue
        elif message.startswith("/chat "):
            recipient = message[len("/chat "):]
            print(Fore.YELLOW + f"\033[F"+f"Chatting with {recipient}"+f"\033[K")
        else:

            try:
                send_tcp(tcp_sock, form_message("MESSAGE", str(id), recipient, message))
            except:
                print(Fore.RED + "Connection lost")
                tcp_sock.close()
                tcp_sock = None

            
        message = input(Fore.CYAN + "me -> " + recipient + ":  ")
    try:
        tcp_sock.close()
    except:return
    print(Fore.YELLOW + "Exited instant messenger")
    print(Style.RESET_ALL)



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
udp_server_address = (hostname, port+1000)
thread = Thread(target=each_client_thread, args=(username, tcp_server_address, udp_server_address))
thread.start()
