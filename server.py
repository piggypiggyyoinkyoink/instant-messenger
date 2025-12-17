import socket
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
global user_dict
user_dict = {}
#mesage format: (code, username, payload)

def commands(data, cid):
    return "Invalid command"

def form_message(code, username, payload):
    return bytes(f"{message_codes[code]}⠀{username}⠀{payload}", "utf-8")


def unpack_message(data:bytes):
    decoded = data.decode()
    parts = decoded.split("⠀")
    print(parts)
    print(decoded)

    code = message_codes[int(parts[0])]
    print("CODE", code)
    username = parts[1]
    payload = parts[2]
    return code, username, payload
    return None, None, None


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
            


def tcp_client_thread(clientsocket, address, lock):
    try:
        print('connection from', address)
        # Receive the data in small chunks and retransmit it
        data = clientsocket.recv(9000)
        code, id, message = unpack_message(data)
        print("CODE:", code)
        print("ID:", id)
        if code == "ID" and id is not None:
            print('Client ID is {}'.format(id))
            cid = id
            user_dict[address] = cid
            response = form_message("GOOD", "SERVER", "ID accepted")
            clientsocket.sendall(response)

            while True:
                data = clientsocket.recv(9000) #what if its over 9000?
                code, id, message = unpack_message(data)
                if code == "COMMAND":
                    clientsocket.sendall(commands(data, cid).encode())
                    continue
                
                print("Received " + message + " from " + cid)
                if data:
                    print('sending data back to the client')
                    response = form_message("GOOD", "SERVER", message)
                    clientsocket.sendall(response)
                else:
                    print('no data from', cid)
                    break
        else:
            print("No ID received, closing connection")
            clientsocket.sendall(form_message("BAD", "SERVER", "No ID received"))
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
thread_tcp = Thread(target=tcp_server_thread, args=(tcp_socket,lock))

#create UDP socket
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_socket.bind((socket.gethostname(), 43000))
thread_udp = Thread(target=udp_server_thread, args=(udp_socket,lock))

t = Thread(target=a, args=(thread_tcp, thread_udp))
t.start()    