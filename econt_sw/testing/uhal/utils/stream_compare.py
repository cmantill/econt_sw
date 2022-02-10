import os
import uhal
import time
from uhal_config import names

import logging
logging.basicConfig()
logger = logging.getLogger('utils')
logger.setLevel(logging.INFO)

def set_trigger(dev,trigger=False):
    """
    - While trigger is 0, it will not generate L1A at all (but of course it will not impede other sources of L1A, either) 
    - While trigger is 1, stream_compare will generate L1A (only for the link capture blocks) on every BX where it sees a mismatch 
    """
    if trigger:
        dev.getNode(names['stream_compare']+".trigger").write(0x1)
        dev.dispatch()
    else:
        dev.getNode(names['stream_compare']+".trigger").write(0x0)
        dev.dispatch()

def configure_compare(dev,nlinks=13,trigger=False):
    """
    Configure comparison lc-ASIC and lc-emulator
    """
    dev.getNode(names['stream_compare']+".control.active_links").write(nlinks)
    dev.dispatch()
    
    set_trigger(dev,trigger)

def reset_log_counters(dev,stime=0.01):
    """
    Reset counters, wait for a time, latch them again.
    Log word and error count
    """
    # reset counters: set counters to zero and immediately continues counting as data comes in
    # latch counters: copies the current counter values to a separate set of registers that you can read out.
    #                 it  continues incrementing the counters, but the copies that you read out don't change (unless you tell it to latch again)
    dev.getNode(names['stream_compare']+".control.reset").write(0x1)
    dev.dispatch()
    time.sleep(stime)
    dev.getNode(names['stream_compare']+".control.latch").write(0x1)
    dev.dispatch()

    word_count = dev.getNode(names['stream_compare']+".word_count").read()
    err_count = dev.getNode(names['stream_compare']+".err_count").read()
    dev.dispatch()
    logger.info('Stream compare, word count %i, error count %i'%(word_count,err_count))

    return err_count
