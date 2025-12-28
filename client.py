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
        raise Exception()
    # Send data
    lock.acquire()
    global status
    status = WAITING
    print(Fore.YELLOW + 'sending {!r}'.format(message.decode("utf-8")))
    tcp_sock.sendall(message)
    t1 = time.time()
    while status == WAITING:
        time.sleep(0.1)
        if time.time() - t1 > 5:
            print(Fore.RED + "Timeout waiting for response")
            break
    lock.release()
    if status == GOOD:
        print(Fore.GREEN + "Message sent successfully")
        return 1
    else:
        print(Fore.RED + "Message failed to send")
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





def client_receive_thread(tcp_sock):
    global status
    while True:
        data = tcp_sock.recv(5000)
        if data:
            code, source_user, dest_user, message = unpack_message(data)
            print(f"Received {message} from {source_user}")
            if source_user == SERVER:
                if code == message_codes["GOOD"]:
                    status = GOOD
                elif code == message_codes["BAD"]:
                    status = BAD
        else:
            print(Fore.RED + "Connection closed by server")
            tcp_sock.close()
            return

def each_client_thread(id, tcp_server_address, udp_server_address):
    TCP = 1
    UDP = 2
    protocol = TCP
    message = ""
    tcp_sock = None
    udp_sock = None
    message = input(Fore.CYAN + "")
    while message != "/kill":
        if protocol == TCP:
            if tcp_sock is None:
                tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                print(Fore.YELLOW + 'connecting to {} port {}'.format(*tcp_server_address))
                tcp_sock.connect(tcp_server_address)
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
                except: 
                    print(Fore.RED + "Failed to setup connection")
                    tcp_sock.close()
                    return
            try:
                send_tcp(tcp_sock, form_message("MESSAGE", str(id), SERVER, message))
            except:
                print(Fore.RED + "Connection lost")
                tcp_sock.close()
                tcp_sock = None

            
        message = input(Fore.CYAN + "")



# Create a TCP/IP socket
try:
    args = sys.argv[1:]
    username, hostname, port = (args[0], args[1], int(args[2]))
except:
    print(Fore.RED + "Invalid command line arguments. Using default values.")
    username, hostname, port = ("default", socket.gethostname(), 42000)
print(username, hostname, port)
tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Connect the socket to the port where the server is listening
tcp_server_address = (hostname, port)
print(Fore.YELLOW + 'connecting to {} port {}'.format(*tcp_server_address))
tcp_sock.connect(tcp_server_address)
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_server_address = (hostname, port+1000)
thread = Thread(target=each_client_thread, args=(username, tcp_server_address, udp_server_address))
thread.start()
