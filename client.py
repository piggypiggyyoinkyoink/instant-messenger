import socket
from threading import Thread

def send_tcp(tcp_sock, message):
    message = bytes(message, 'utf-8')
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

def each_client_thread(id, tcp_server_address, udp_server_address):
    TCP = 1
    UDP = 2
    protocol = TCP
    message = ""
    tcp_sock = None
    udp_sock = None
    message = input()
    while message != "/kill":
        if message == "/tcp":
            protocol = TCP
            if udp_sock is not None:
                udp_sock.close()
                udp_sock = None
        elif message == "/udp":
            protocol = UDP
            if tcp_sock is not None:
                tcp_sock.close()
                tcp_sock = None
        else:

            if protocol == TCP:
                if tcp_sock is None:
                    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    print('connecting to {} port {}'.format(*tcp_server_address))
                    tcp_sock.connect(tcp_server_address)
                    try:
                        #send id
                        send_tcp(tcp_sock, f'ID:{id}')
                    except: 
                        print("Failed to setup connection")
                        tcp_sock.close()
                        return
                try:
                    send_tcp(tcp_sock, message)
                except:
                    print("Connection lost")
                    tcp_sock.close()
                    tcp_sock = None

            elif protocol == UDP:
                if udp_sock is None:
                    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    send_udp(udp_sock, udp_server_address, f'ID:{id}')
                try:
                    send_udp(udp_sock, udp_server_address, message)
                except:
                    print("Connection lost")
                    udp_sock.close()
                    udp_sock = None
        
        message = input()



# Create a TCP/IP socket
id = 1
tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Connect the socket to the port where the server is listening
tcp_server_address = (socket.gethostname(), 42000)
print('connecting to {} port {}'.format(*tcp_server_address))
tcp_sock.connect(tcp_server_address)
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_server_address = (socket.gethostname(), 43000)
thread = Thread(target=each_client_thread, args=(id, tcp_server_address, udp_server_address))
thread.start()


