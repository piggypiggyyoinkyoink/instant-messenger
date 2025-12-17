import socket
from threading import Thread
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
#mesage format: code⠀username⠀payload

def form_message(code, username, payload):
    return bytes(f"{message_codes[code]}⠀{username}⠀{payload}", "utf-8")

def unpack_message(data:bytes):
    try:
        decoded = data.decode()
        parts = decoded.split("⠀")
        code = int(parts[0])
        username = parts[1]
        payload = parts[2]
        return code, username, payload
    except:
        return None, None, None


def send_tcp(tcp_sock, message):
    if type(message) is not bytes:
        raise Exception()
    # Send data
    print('sending {!r}'.format(message.decode("utf-8")))
    tcp_sock.sendall(message)

    # Look for the response
    amount_received = 0
    amount_expected = len(message)

    while amount_received < amount_expected:
        data = tcp_sock.recv(5000)
        if not data:
            break
        amount_received += len(data)
        print('received {!r}'.format(data.decode("utf-8")))
    return



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
    while True:
        data = tcp_sock.recv(5000)
        if data:
            code, id, message = unpack_message(data)
            print(f"Received {message} from {id}")
        else:
            print("Connection closed by server")
            tcp_sock.close()
            return

def each_client_thread(id, tcp_server_address, udp_server_address):
    TCP = 1
    UDP = 2
    protocol = TCP
    message = ""
    tcp_sock = None
    udp_sock = None
    message = input()
    while message != "/kill":
        if protocol == TCP:
            if tcp_sock is None:
                tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                print('connecting to {} port {}'.format(*tcp_server_address))
                tcp_sock.connect(tcp_server_address)
                # currently broken (using same socket is bad?)
                # rec_thread = Thread(target=client_receive_thread, args=(tcp_sock,))
                # rec_thread.start()
                try:
                    #send id
                    send_tcp(tcp_sock, form_message("ID", str(id), str(id)))
                except: 
                    print("Failed to setup connection")
                    tcp_sock.close()
                    return
            try:
                send_tcp(tcp_sock, form_message("MESSAGE", str(id), message))
            except:
                print("Connection lost")
                tcp_sock.close()
                tcp_sock = None

            
        message = input()



# Create a TCP/IP socket
id = "bob"
tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Connect the socket to the port where the server is listening
tcp_server_address = (socket.gethostname(), 42000)
print('connecting to {} port {}'.format(*tcp_server_address))
tcp_sock.connect(tcp_server_address)
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_server_address = (socket.gethostname(), 43000)
thread = Thread(target=each_client_thread, args=(id, tcp_server_address, udp_server_address))
thread.start()
