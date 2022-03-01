#!/usr/bin/env python3  
import zmq
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start hexacontroller server')
    parser.add_argument('--server', type=str,
                        default='6677',
                        help='server for uhal hexacontroller')
    args = parser.parse_args()

    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:%s"%args.server)
    print('[ZMQ] Server started')

    from hexactrl_interface import hexactrl_interface
    hexactrl = hexactrl_interface()

    while True:
        string = socket.recv_string().lower()
        if string == "configure":
            ans = hexactrl.configure()
            socket.send_string("ready")
        elif string == "reset":
            ans = hexactrl.reset()
            socket.send_string("ready")
        elif string == "latch":
            ans = hexactrl.latch()
            socket.send_string(ans)
