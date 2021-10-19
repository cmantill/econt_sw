import uhal
import time
import argparse
import numpy as np
import logging
logging.basicConfig()

from uhal_config import names,input_nlinks,output_nlinks

"""
Delay scan using uHAL python2.

Usage:
   python testing/uhal-delayScan.py 
"""

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE, NONE",default='NONE')
    
    args = parser.parse_args()

    if args.logLevel.find("ERROR")==0:
        uhal.setLogLevelTo(uhal.LogLevel.ERROR)
    elif args.logLevel.find("WARNING")==0:
        uhal.setLogLevelTo(uhal.LogLevel.WARNING)
    elif args.logLevel.find("NOTICE")==0:
        uhal.setLogLevelTo(uhal.LogLevel.NOTICE)
    elif args.logLevel.find("DEBUG")==0:
        uhal.setLogLevelTo(uhal.LogLevel.DEBUG)
    elif args.logLevel.find("INFO")==0:
        uhal.setLogLevelTo(uhal.LogLevel.INFO)
    else:
        uhal.disableLogging()

    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")

    logger = logging.getLogger('delayScan')
    logger.setLevel(logging.INFO)
    
    fromIO_settings = {"reg0.tristate_IOBUF": 0,
                       "reg0.bypass_IOBUF": 0,
                       "reg0.reset_counters": 1,
                       "reg0.invert": 0,
                       }
    
    # set delay and wait until delay is ready
    def set_delay(link,delay):
        delay = 0 if delay<0 else delay
        delay = 503 if delay>503 else delay # 503+8=511
        
        # configure IO block                                                                                                                                                                                   
        for key,value in fromIO_settings.items():
            dev.getNode(names['IO']['from']+".link%i"%link+"."+key).write(value)
            
        dev.getNode(names['IO']['from']+".link%i"%link+".reg0.delay_mode").write(0x0) # delay mode to manual
        dev.getNode(names['IO']['from']+".link%i"%link+".reg0.delay_in").write(delay) # set delay
        dev.getNode(names['IO']['from']+".link%i"%link+".reg0.delay_offset").write(8) # delay offset
        dev.getNode(names['IO']['from']+".link%i"%link+".reg0.delay_set").write(1) 
        dev.getNode(names['IO']['from']+".link%i"%link+".reg0.reset_counters").write(0x0)
        dev.dispatch()
        
        while 1:
            delay_ready = dev.getNode(names['IO']['from']+".link%i"%link+".reg3.delay_ready").read()
            delay_out = dev.getNode(names['IO']['from']+".link%i"%link+".reg3.delay_out").read()
            dev.dispatch()
            if delay_out==delay and delay_ready==1:
                return True
            else:
                time.sleep(0.001)
        return True

    bitcounts = {}
    errorcounts = {}
    for l in range(output_nlinks):
        bitcounts[l] = []
        errorcounts[l] = []
        
    for delay in range(0,504,8):
        # set delays and wait until delay ready
        for l in range(output_nlinks):
            set_delay(l,delay)

        # reset the counters (reset will clear itself)
        dev.getNode(names['IO']['from']+".global.global_reset_counters").write(1)
        time.sleep(0.001)
        # latch the counters (saves counter values for all links)
        dev.getNode(names['IO']['from']+".global.global_latch_counters").write(1)

        for l in range(output_nlinks):
            # read bit_counter (counts the number of bytes)
            # and error_counter (counts the number of bytes that had at least one bit error - that did not match between P and N side)
            bit_counts = dev.getNode(names['IO']['from']+".link%i"%l+".bit_counter").read()
            error_counts = dev.getNode(names['IO']['from']+".link%i"%l+".error_counter").read()
            dev.dispatch()
            bitcounts[l].append(int(bit_counts))
            errorcounts[l].append(int(error_counts))

    print(bitcounts)
    print(errorcounts)
