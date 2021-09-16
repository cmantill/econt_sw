#!/usr/bin/env python3

import zmq
import yaml
import econ_interface
import argparse
import functools

def redirect(fn):
    socket.send_string('READY')
    cfg_str  = socket.recv_string()
    cfg_yaml = yaml.safe_load(cfg_str)
    ans_yaml = fn(cfg_yaml)
    ans_str  = yaml.dump(ans_yaml, default_flow_style=False)
    socket.send_string(ans_str)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start i2c server')
    parser.add_argument('--addr', type=functools.partial(int, base=0),
                        default=0x20,
                        help='i2c address')
    args = parser.parse_args()

    """ ZMQ-Server: Redirect user request to Board. """
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5555")
    print('[ZMQ] Server started')
    
    try:
        board = econ_interface.econ_interface(args.addr)
        
        while True:
            string = socket.recv_string().lower()
            if string == "initialize" or string == "configure":
                if board: redirect(board.configure)
                else: socket.send_string("E: Board not initialized.")
            elif string == "read": 
                redirect(board.read)

    except KeyboardInterrupt:
        print('\nClosing server.')
        socket.close()
        context.term()
