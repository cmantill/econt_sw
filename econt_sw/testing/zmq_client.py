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

    def recv_array(socket, flags=0, copy=True, track=False):
        """recv a numpy array"""
        md = socket.recv_json(flags=flags)
        print(md)
        msg = socket.recv(flags=flags, copy=copy, track=track)
        print(msg)
        buf = memoryview(msg)
        A = numpy.frombuffer(buf, dtype=md["dtype"])
        return A.reshape(md["shape"])

    def send(socket, cmd, cfg=""):
        """send routine"""
        socket.send(cmd.encode())
        status = socket.recv_string()
        if status == 'ready':
            socket.send_string(cfg)
            answer = str(socket.recv_string())
            if answer == "data":
                answer = recv_array(socket, flags=0, copy=True, track=False)
                return(answer)
            else:
                return(answer)
        else:
            return(status)

    # note: define alternative IP in zmq_server too?
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:%s"%args.server)
    
    # configure
    ans = send(socket,"configure")
    print(ans)
    # reset counters

    ans = send(socket,"reset")
    print(ans)
    
    # latch and get errors
    from datetime import datetime
    dt = datetime.timestamp(datetime.now())
 
    ret_array = send(socket,"latch",f"{dt}")
    print('re array ',ret_array)
