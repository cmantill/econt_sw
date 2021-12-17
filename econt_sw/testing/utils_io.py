import os
import uhal
from uhal_config import names,input_nlinks,output_nlinks

import logging
logging.basicConfig()
logger = logging.getLogger('utils')
logger.setLevel(logging.INFO)

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

    # reset
    dev.getNode(names[io_name][io]+".global.global_rstb_links").write(0x1)
    dev.getNode(names[io_name][io]+".global.global_reset_counters").write(0x1)
    import time
    time.sleep(1)
    dev.getNode(names[io_name][io]+".global.global_latch_counters").write(0x1)
    dev.dispatch()

def check_IO(dev,io='from',nlinks=output_nlinks,io_name='IO',nit=10000):
    """
    Checks whether IO block is aligned.
    """
    # reset the counters
    dev.getNode(names[io_name][io]+".global.global_reset_counters").write(0x1)
    import time
    time.sleep(1)
    dev.getNode(names[io_name][io]+".global.global_latch_counters").write(0x1)
    dev.dispatch()
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
            logger.info("%s-IO link%i: bit_tr %d, delay ready %d, error counter %i, bit_counter %i"%(io,l,bit_tr,delay_ready,error_counter,bit_counter))
            if delay_ready == 1:
                break
        IO_delayready.append(delay_ready)
    is_aligned = True
    for delay in IO_delayready:
        if delay!=1:
            is_aligned = False
    if is_aligned:
        logging.info("Links %s-IO are aligned"%io)
    else:
        logging.info("Links %s-IO are not aligned"%io)
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
    return is_aligned
    
