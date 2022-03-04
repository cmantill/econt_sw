#!/usr/bin/env python3

import zmq
import argparse
import numpy as np
from zmq_controller import daqController

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start hexacontroller client')
    parser.add_argument('--server', type=str,
                        default='6677',
                        help='server for uhal hexacontroller')
    args = parser.parse_args()
    
    daq_socket = daqController("localhost", str(args.server))

    daq_socket.configure()
    daq_socket.reset_counters()
    try:
        print("Press Ctrl-C to terminate while statement")
        while True:
            daq_socket.latch_counters()
    except KeyboardInterrupt:
        pass
