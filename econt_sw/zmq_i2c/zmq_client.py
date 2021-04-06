#!/usr/bin/env python3

import zmq
from yaml import safe_load, dump

# send routine
def send(cmd, cfg=""):
    socket.send(cmd.encode())
    status = socket.recv_string()
    if status == 'READY':
        socket.send_string(cfg)
        answer = str(socket.recv_string())
        return(answer)
    else:
        return(status)

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5555")

# test alignment
ret = send("initialize", './configs/init_align.yaml')
print('ret ',ret)

print("\n --- READ: --- \n")
ret = send("read", './configs/init_align.yaml')
print('ret ',ret)
print("---")
