#!/usr/bin/env python3  
import zmq
import argparse
import numpy as np
import logging
import sys

def _init_logger():
    logger = logging.getLogger('daqserver')
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

class daqServer():
    def __init__(self,server):
        context = zmq.Context()
        self.socket = context.socket(zmq.REP)
        self.socket.bind("tcp://*:%s"%server)
        self.logger = _init_logger()
        self.logger.info('[ZMQ] Server started')

        from hexactrl_interface import hexactrl_interface
        self.hexactrl = hexactrl_interface()

        self.data = None
        
    def send_array(self, A, flags=0, copy=True, track=False):
        """send a numpy array with metadata"""
        md = dict(
            dtype=str(A.dtype),
            shape=A.shape,
        )
        self.socket.send_json(md, flags | zmq.SNDMORE)
        return self.socket.send(A, flags, copy=copy, track=track)

    def get_string(self):
        return self.socket.recv_string().lower()

    def latch_counters(self,timestamp):
        err_counter,daq_data = daq.hexactrl.latch_counters(timestamp)
        self.socket.send_string(f"{err_counter}")
        if err_counter>0:
            self.data = daq_data

    def get_data(self):
        self.send_array(self.data, copy=False)
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start hexacontroller server')
    parser.add_argument('--server', type=str,
                        default='6677',
                        help='server for uhal hexacontroller')
    args = parser.parse_args()

    daq = daqServer(args.server)

    while True:
        string = daq.get_string()
        if string == "configure":
            ans = daq.hexactrl.configure()
            daq.socket.send_string("conf")
        elif string == "reset_counters":
            ans = daq.hexactrl.reset_counters()
            daq.socket.send_string("ready")
        elif string.startswith("latch"):
            if len(string.split())>1:
                timestamp=string.split()[1]
            else:
                timestamp=""
            daq.latch_counters(timestamp)
        elif string == "daq":
            daq.get_data()
