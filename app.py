import socketserver
from constant import *
from network import WSHandler

if __name__ == '__main__':
    print('Simple websocket server')
    with socketserver.TCPServer((HOST, PORT), WSHandler) as server:
        server.serve_forever()
