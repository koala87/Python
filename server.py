#!/usr/bin/env python

"""
@Function: TCP server demo
@Author: Yingqi Jin
@Date: Nov. 3, 2015
"""

import SocketServer
import struct
import pdb


def parseByte(code):
    return struct.unpack('iiiiii', code)


class RequestHandle(SocketServer.BaseRequestHandler):
    def handle(self):
        while True:
            data = self.request.recv(1024)
            if len(data) > 0:
                self.request.send(data)
                print parseByte(data) 
                continue
            else:
                break
        self.request.close()

if __name__ == "__main__":

    serv = SocketServer.ThreadingTCPServer( ("", 6000), RequestHandle)

    serv.serve_forever()

    
