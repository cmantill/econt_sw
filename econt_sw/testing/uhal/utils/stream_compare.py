import os
import uhal
import time
from uhal_config import names

import logging
logging.basicConfig()
logger = logging.getLogger('utils')
logger.setLevel(logging.INFO)

def compare(dev,nlinks=13,stime=0.01):
    """
    Compare lc ASIC and lc Emulator
    """
    dev.getNode(names['stream_compare']+".control.active_links").write(nlinks)
    dev.getNode(names['stream_compare']+".trigger").write(0x0)
    dev.dispatch()

    dev.getNode(names['stream_compare']+".control.reset").write(0x1)
    time.sleep(stime)
    dev.getNode(names['stream_compare']+".control.latch").write(0x1)
    dev.dispatch()

    word_count = dev.getNode(names['stream_compare']+".word_count").read()
    err_count = dev.getNode(names['stream_compare']+".err_count").read()
    dev.dispatch()
    logger.info('Stream compare, word count %i, error count %i'%(word_count,err_count))

    
