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
        return self.socket.recv_string()

    def start_daq(self):
        ans = self.hexactrl.start_daq()
        self.socket.send_string("ready")

    def stop_daq(self,timestamp):
        err_counter,daq_data = daq.hexactrl.stop_daq(timestamp)
        self.socket.send_string(f"{err_counter}")
        if err_counter>0:
            self.data = daq_data

    def get_data(self):
        self.send_array(self.data, copy=False)

    def reset_pll_count(self):
        ans=self.hexactrl.resetPLLLockCount()
        self.socket.send_string(ans)

    def get_pll_count(self):
        ans=self.hexactrl.getPLLLockCount()
        self.socket.send_string(f"{ans}")

    def setTestVectors(self,string):
        #split string into arguments, and pass along to hexacontroller testVectors
        args=string.split()[1:]
        ans=self.hexactrl.testVectors(args)
        self.socket.send_string(ans)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start hexacontroller server')
    parser.add_argument('--server', type=str,
                        default='6677',
                        help='server for uhal hexacontroller')
    args = parser.parse_args()

    daq = daqServer(args.server)

    while True:
        fullstring = daq.get_string()
        string=fullstring.lower()
        if string == "configure":
            ans = daq.hexactrl.configure()
            daq.socket.send_string("conf")
        elif string == "startdaq":
            daq.start_daq()
        elif string.startswith("stopdaq"):
            if len(string.split())>1:
                timestamp=string.split()[1]
            else:
                timestamp=""
            daq.stop_daq(timestamp)
        elif string == "getdata":
            daq.get_data()
        elif string == "resetpll":
            daq.reset_pll_count()
        elif string == "getpll":
            daq.get_pll_count()
        elif string.startswith("testvector"):
            daq.setTestVectors(fullstring)
