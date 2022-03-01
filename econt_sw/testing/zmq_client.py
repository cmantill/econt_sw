#!/usr/bin/env python3

import zmq
from yaml import safe_load, dump
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start hexacontroller client')
    parser.add_argument('--server', type=str,
                        default='6677',
                        help='server for uhal hexacontroller')
    args = parser.parse_args()

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

    # note: define alternative IP in zmq_server too?
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:%s"%args.server)
    
    # configure
    ret = send("configure")
    
    # reset counters
    ret = send("reset")

    # latch and get errors
    ret = send("latch")
    print('ret ',ret)
