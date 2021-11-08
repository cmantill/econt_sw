import uhal
import time
import argparse
import logging
logging.basicConfig()

from uhal_config import names,input_nlinks,output_nlinks
from uhal_utils import get_captured_data,save_testvector,configure_IO,check_IO,configure_acquire,acquire
from uhal-capture_on_ASIC import getInputData
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

    logger = logging.getLogger('align:ASIC')
    logger.setLevel(logging.INFO)

    # configure IO blocks
    for io in names['ASIC-IO'].keys():
        configure_IO(dev,io,'ASIC-IO')
    raw_input("IO blocks configured. Waiting for bit transitions. Press key to continue...")

    # check that to-IO is aligned
    check_IO(dev,'to',nlinks=input_nlinks,io_name='ASIC-IO')
    
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
            dev.getNode(lcapture_input["lc"]+".link%i"%l+".align_pattern").write(sync_patterns[lcapture])

    # check PRBS input?
    checkPRBS = True
    if checkPRBS:
        input_data=getInputData("BX",300)
        printData = True
        if printdata:
            data = [[hex(input_data[j][i]) for j in range(len(input_data))] for i in range(len(input_data[0]))]
            # print first 10 BXs...
            for d in data[:10]:
                print(d)

    # read counters
    reset_roc = dev.getNode(names['ASIC-fc-recv']+".counters.link_reset_roct").read()
    dev.dispatch()
    reset_econt = dev.getNode(names['ASIC-fc-recv']+".counters.link_reset_econt").read()
    dev.dispatch()
    logger.info("Initial counters: link reset roct %d, econt %d"%(reset_roc,reset_econt))
    raw_input("Link capture and counters checked. Waiting for link reset ROCt to align input link capture")

    # read fc again
    reset_roc = dev.getNode(names['ASIC-fc-recv']+".counters.link_reset_roct").read()
    dev.dispatch()
    reset_econt = dev.getNode(names['ASIC-fc-recv']+".counters.link_reset_econt").read()
    dev.dispatch()
    logger.info("After counters: reset roct %d, econt %d"%(reset_roc,reset_econt))

    # check that input lc is aligned
    isaligned_input = check_links(dev,"ASIC-lc-input",input_nlinks)
    if isaligned_input:
        logger.info("ASIC-lc-input is aligned")
    else:
        logger.warning("ASIC-lc-input is not aligned")
    exit(1)
