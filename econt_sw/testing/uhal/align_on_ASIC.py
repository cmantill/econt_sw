import uhal
import time
import argparse
import logging
logging.basicConfig()

from utils.uhal_config import *
import utils.link_capture as utils_lc
import utils.io as utils_io
import utils.test_vectors as utils_tv

"""
Alignment sequence on 'ASIC' - (emulator) using python2 uhal.

Usage:
   python testing/uhal-align_on_ASIC.py 
"""

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE, NONE",default='NONE')
    args = parser.parse_args()
    
    set_logLevel(args)
    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")

    logger = logging.getLogger('alignASIC')
    try:
        logger.setLevel(args.logLevel)
    except ValueError:
        logging.error("Invalid log level")
        exit(1)


    # configure IO blocks
    for io in names['ASIC-IO'].keys():
        utils_io.configure_IO(dev,io,'ASIC-IO')
    raw_input("IO blocks configured. Waiting for bit transitions. Press key to continue...")

    # check that to-IO is aligned
    utils_io.check_IO(dev,'to',nlinks=input_nlinks,io_name='ASIC-IO')
    
    # configure link captures
    sync_patterns = {"ASIC-lc-input": 0xaccccccc,
                     "ASIC-lc-output": 0x122,
                 }
    for lcapture in ["ASIC-lc-input","ASIC-lc-output"]:
        dev.getNode(names[lcapture]["lc"]+".global.link_enable").write(0x1fff)
        dev.getNode(names[lcapture]["lc"]+".global.link_enable").write(0x1fff)
        dev.getNode(names[lcapture]["lc"]+".global.explicit_resetb").write(0x0)
        time.sleep(0.001)
        dev.getNode(names[lcapture]["lc"]+".global.explicit_resetb").write(0x1)
        dev.dispatch()
        nlinks = input_nlinks if "input" in lcapture else output_nlinks
        for l in range(nlinks):
            dev.getNode(names[lcapture]["lc"]+".link%i"%l+".align_pattern").write(sync_patterns[lcapture])

    # check PRBS input?
    checkPRBS = True
    if checkPRBS:
        utils_lc.configure_acquire(dev,"ASIC-lc-input","BX",4095,input_nlinks)
        utils_lc.do_capture(dev,["ASIC-lc-input"])
        input_data = utils_lc.get_captured_data(dev,"ASIC-lc-input",4095,input_nlinks)
        saveData = True
        if saveData:
            utils_tv.save_testvector("ASIC-lc-input-prbs.csv", input_data)

    # read counters
    reset_roc = dev.getNode(names['ASIC-fc-recv']+".counters.link_reset_roct").read()
    dev.dispatch()
    reset_econt = dev.getNode(names['ASIC-fc-recv']+".counters.link_reset_econt").read()
    dev.dispatch()
    logger.info("Initial counters: link reset roct %d, econt %d"%(reset_roc,reset_econt))

    # save input data?
    saveInputData = True
    if saveInputData:
        utils_lc.configure_acquire(dev,"ASIC-lc-input","linkreset_ROCt",4095,input_nlinks)
        utils_lc.do_capture(dev,["ASIC-lc-input"])
        input_data = utils_lc.get_captured_data(dev,"ASIC-lc-input",4095,input_nlinks)
        utils_tv.save_testvector("ASIC-lc-input.csv", input_data)
    else:
        raw_input("Link capture and counters checked. Waiting for link reset ROCt to align input link capture")

    # read fc again
    reset_roc = dev.getNode(names['ASIC-fc-recv']+".counters.link_reset_roct").read()
    dev.dispatch()
    reset_econt = dev.getNode(names['ASIC-fc-recv']+".counters.link_reset_econt").read()
    dev.dispatch()
    logger.info("After counters: reset roct %d, econt %d"%(reset_roc,reset_econt))

    # check that input lc is aligned
    isaligned_input = utils_lc.check_links(dev,"ASIC-lc-input",input_nlinks,use_np=False)
    if isaligned_input:
        logger.info("ASIC-lc-input is aligned")
    else:
        logger.warning("ASIC-lc-input is not aligned")
    exit(1)
