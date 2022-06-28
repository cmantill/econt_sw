#!/usr/bin/python3
from urllib.request import urlopen
import time
import sys
import os
sys.path.append( 'testing' )
from i2c import call_i2c 

from datetime import datetime
import argparse

import zmq
import yaml

from zmq_controller import daqController

URL='https://www-bd.fnal.gov/notifyservlet/www'
Pulse_SC_time=6

def getOffset():
    offset=0
    response = urlopen(URL).read()
    _scTime,nsteps_SC=str(response).split('SC time</a> = ')[1].split(' </td>')[0].split(' / ')
    _scTime,nsteps_SC=float(_scTime), float(nsteps_SC)
    _time=round((time.time()-offset)%nsteps_SC,1)
    offset=round((_time-_scTime)%nsteps_SC,1)
    return _scTime, nsteps_SC, offset

def main(yaml_config=None, snapshot=False, testVector=None, tag=""):

#    uhalClient=daqController('192.168.1.48','6677')

    logging.debug('Starting uhal config')
    _time, nsteps_SC, localSCOffset=0,0,0
 
    dataStarted=False
    waiting_for_pulse=False
    dataFinished=True
    i2c_check_done=True
    snapshotTaken=True
    oot_dataStarted=True
    oot_dataFinished=True
    manualPLLUnlocked=True
    RO_status_captured=True
    done=True

    doPRBScheck=False

    previousLoLCount=-1

    i=0
    try:
        while True:
            if (i%100)==0:
                logging.debug(f'Resync Time:')
                logging.debug(f'Old: {_time}, {nsteps_SC}, {localSCOffset}')
                _time, nsteps_SC, localSCOffset=getOffset()
                i = 1
                logging.debug(f'New: {_time}, {nsteps_SC}, {localSCOffset}')
            else:
                _time=round((time.time()-localSCOffset)%nsteps_SC,1)
                i += 1

            # logging.info(f'{_time} / {nsteps_SC}')

            if (_time > (Pulse_SC_time - 5)%nsteps_SC) and _time<Pulse_SC_time and not dataStarted:
                logging.debug(f'Starting data comparisons')
                dataStarted=True
                waiting_for_pulse=True

            elif (_time > Pulse_SC_time) and waiting_for_pulse:
                logging.info(f'PULSE IS COMING:')
                waiting_for_pulse=False
                i2c_check_done=False
                done=False

            elif (_time > (Pulse_SC_time+15)%nsteps_SC) and not i2c_check_done:
                x = time.time()
                logging.info(f'CHECK I2C STATUS:')
                call_i2c(args_yaml='configs/startup.yaml',args_write=True,args_ip='192.168.206.48')
                i2c_check_done=True
                dataStarted=False
                done=True

            time.sleep(1)

    except KeyboardInterrupt:
        logging.info(f'Closing')


if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--logName', default='logFile.log', help='log name')
    parser.add_argument('--yaml', default=None, help='Name of yaml file to load')
    parser.add_argument('--testVector', default=None, help='type of test vector to send (csv file, or command such as PRBS, PRBS28, etc)')
    parser.add_argument('--tag', default="", help='extra information to add to the timestamp in daq comparisons')
    parser.add_argument('--snapshot', default=False, action='store_true', help='take snapshot after each read')

    parser.add_argument('--debug', default=False, action='store_true', help='print local SC time to debug')
    args = parser.parse_args()

    import logging
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)-6s %(message)s',
                        datefmt='%m-%d-%y %H:%M:%S',
                        filename=args.logName,
                        filemode='a')
    
    console = logging.StreamHandler()
    if args.debug:
        console.setLevel(logging.DEBUG)
    else:
        console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)-6s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger().addHandler(console)

    main(yaml_config=args.yaml, snapshot=args.snapshot, testVector=args.testVector)
