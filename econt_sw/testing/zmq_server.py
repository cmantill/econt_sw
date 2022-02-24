#!/usr/bin/env python3  
import zmq

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:6677")
print('[ZMQ] Server started')

from hexactrl_interface import hexactrl_interface
hexactrl = hexactrl_interface()

while True:
    string = socket.recv_string().lower()
    if string == "init":
        ans = hexactrl.init()
        socket.send_string("ready")
