#!/usr/bin/env python

"""
TCP Client Demo
"""

import socket
import time
import struct

address = ('127.0.0.1', 6000)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

s.connect(address)

print 'connect to server ...'

body = "hello world"
header = [17, 100, 10001, len(body), 65536, 1001]

pack = struct.pack('iiiiii', header[0], header[1], header[2],
        header[3], header[4], header[5])

while True:
    s.send(pack)
    time.sleep(2)

s.close()
