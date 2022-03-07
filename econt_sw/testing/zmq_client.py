#!/usr/bin/env python3

import zmq
import argparse
import numpy as np
import time
from datetime import datetime
from zmq_controller import daqController

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start hexacontroller client')
    parser.add_argument('--server', type=str,
                        default='6677',
                        help='server for uhal hexacontroller')
    parser.add_argument('--tag', type=str,
                        default='rpt',
                        help='tag for dataset')
    args = parser.parse_args()

    daq_socket = daqController("192.168.1.48", str(args.server))
    print(daq_socket.configure())
    try:
        print("Press Ctrl-C to terminate while statement")
        while True:
            daq_socket.start_daq()
            ## TODO: add fixed time between reset and latch counters ?
            dateTimeObj = datetime.now()
            timestamp = args.tag + dateTimeObj.strftime("%d%b_%H%M%S")
            daq_arrays = daq_socket.stop_daq(timestamp)
            time.sleep(15) 
    except KeyboardInterrupt:
        pass
