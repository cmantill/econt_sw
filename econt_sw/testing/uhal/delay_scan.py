import uhal
import time
import argparse
import logging
logging.basicConfig()

from uhal_config import *

"""
Delay scan using uHAL python2.

Usage:
   python testing/uhal-delayScan.py 
"""

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE",default='INFO')
    args = parser.parse_args()

    set_logLevel(args)
    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")

    logger = logging.getLogger('delayScan')
    try:
        logger.setLevel(args.logLevel)
    except ValueError:
        logging.error("Invalid log level")
        exit(1)
    
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
            delay_out_N = dev.getNode(names['IO']['from']+".link%i"%link+".reg3.delay_out_N").read()
            dev.dispatch()
            if delay_out==delay and delay_ready==1:
                print('delay out ',int(delay_out),int(delay_out_N))
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
