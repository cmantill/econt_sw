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
            socket.send_string("Configure ready")
        elif string == "reset":
            ans = hexactrl.reset()
            socket.send_string("Reset ready")
        elif string == "latch":
            socket.send_string("ready")
            timestamp = socket.recv_string().lower()
            from datetime import datetime
            dt = datetime.fromtimestamp(float(timestamp))
            err_counter,first_rows = hexactrl.latch(dt)
            if err_counter>0:
                socket.send_string("data")
                A = first_rows["lc-input"]
                md = dict(
                    dtype=str(A.dtype),
                    shape=A.shape,
                )
                socket.send_json(md, zmq.SNDMORE)
                socket.send(A, flags=0, copy=True, track=False)
            else:
                socket.send_string("Latch with no errors")
