import os
import uhal
from uhal_config import names,input_nlinks,output_nlinks

import time
import logging
logging.basicConfig()
logger = logging.getLogger('utils:IO')
logger.setLevel(logging.INFO)

def reset_counters(dev,io,io_name='IO'):
    dev.getNode(names[io_name][io]+".global.global_reset_counters").write(0x1)
    time.sleep(1)
    dev.getNode(names[io_name][io]+".global.global_latch_counters").write(0x1)
    dev.dispatch()

def configure_IO(dev,io,io_name='IO',invert=False):
    """
    Configures IO blocks.
    """
    ioblock_settings = {
        "reg0.tristate_IOBUF": 0,
        "reg0.bypass_IOBUF": 0,
        "reg0.invert": 0,
        "reg0.reset_link": 0,
        "reg0.reset_counters": 1,
        "reg0.delay_mode": 0, 
    }
    nlinks = input_nlinks if io=='to' else output_nlinks
    # set delay mode to 1 to those blocks that need to be aligned
    if (io_name == "ASIC-IO" and io=="to") or (io_name == "IO" and io=="from"):
        ioblock_settings["reg0.delay_mode"] = 1
        delay_mode = 1
    # set invert to 1
    if invert:
        ioblock_settings["reg0.invert"] = 1

    # set 
    for l in range(nlinks):
        for key,value in ioblock_settings.items():
            dev.getNode(names[io_name][io]+".link"+str(l)+"."+key).write(value)
        dev.dispatch()

    # reset links
    dev.getNode(names[io_name][io]+".global.global_rstb_links").write(0x1)
    dev.dispatch()

    # reset counters
    reset_counters(dev,io,io_name)

def manual_IO(dev,io,io_name='IO'):
    nlinks = input_nlinks if io=='to' else output_nlinks

    # read delays found by automatic delay setting
    delay_P,delay_N = get_delay(dev,io,nlinks=nlinks,io_name=io_name,verbose=False)

    # set delay mode to 0 and delays to what we found
    for l in range(nlinks):
        dev.getNode(names[io_name][io]+".link"+str(l)+".reg0.delay_mode").write(0)
        dev.getNode(names[io_name][io]+".link"+str(l)+".reg0.delay_in").write(delay_P[0])
        dev.getNode(names[io_name][io]+".link"+str(l)+".reg0.delay_offset").write(8) # fix this to 8
    dev.dispatch()

    # reset counters
    reset_counters(dev,io,io_name)

def check_IO(dev,io='from',nlinks=output_nlinks,io_name='IO',nit=10000,verbose=False):
    """
    Checks whether IO block is aligned.
    """
    # reset the counters
    reset_counters(dev,io,io_name)

    # check the counters
    IO_delayready = []
    for l in range(nlinks):
        i=0
        delay_ready=0
        while i < nit:
            i+=1
            bit_tr = dev.getNode(names[io_name][io]+".link"+str(l)+".reg3.waiting_for_transitions").read()
            delay_ready = dev.getNode(names[io_name][io]+".link"+str(l)+".reg3.delay_ready").read()
            error_counter = dev.getNode(names[io_name][io]+".link"+str(l)+".error_counter").read()
            bit_counter = dev.getNode(names[io_name][io]+".link"+str(l)+".bit_counter").read()
            dev.dispatch()
            if verbose or error_counter>0:
                logger.info("%s-IO link%i: bit_tr %d, delay ready %d, error counter %i, bit_counter %i"%(io,l,bit_tr,delay_ready,error_counter,bit_counter))
            if delay_ready == 1:
                break
        IO_delayready.append(delay_ready)
    is_aligned = True
    for delay in IO_delayready:
        if delay!=1:
            is_aligned = False
    if is_aligned:
        logger.info("Links %s-IO are aligned"%io)
    else:
        logger.info("Links %s-IO are not aligned"%io)
    return is_aligned

def print_IO(dev,io='from',nlinks=output_nlinks,io_name='IO'):
    regs = ["reg0.reset_link","reg0.reset_counters","reg0.delay_mode","reg0.delay_set","reg0.bypass_IOBUF","reg0.tristate_IOBUF","reg0.latch_counters","reg0.delay_in","reg0.delay_offset","reg0.invert",
            "bit_counter","error_counter",
            "reg3.delay_ready","reg3.delay_out","reg3.delay_out_N","reg3.waiting_for_transitions",
        ]
    for l in range(nlinks):
        vals = {}
        for reg in regs:
            tmp = dev.getNode(names[io_name][io]+".link"+str(l)+"."+reg).read()
            dev.dispatch()
            vals[reg] = int(tmp)
        logger.info("%s-IO link%i: %s"%(io,l,vals))

def get_delay(dev,io='from',nlinks=output_nlinks,io_name='IO',verbose=True):
    delay_P = {}
    delay_N = {}
    for link in range(nlinks):
        delay_out = dev.getNode(names['IO'][io]+".link%i"%link+".reg3.delay_out").read()
        delay_out_N = dev.getNode(names['IO'][io]+".link%i"%link+".reg3.delay_out_N").read()
        dev.dispatch()
        if verbose:
            logger.info("link %i: delay_out %i delay_out_N %i"%(link,delay_out,delay_out_N))
        delay_P[link] = int(delay_out)
        delay_N[link] = int(delay_out_N)
    return delay_P,delay_N
