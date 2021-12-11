import uhal
import time
import argparse
import logging
logging.basicConfig()

from uhal_config import names,input_nlinks,output_nlinks
import utils_lc,utils_tv

"""
Alignment sequence on 'ASIC' - (emulator) using python2 uhal.

Usage:
   python testing/uhal-align_on_ASIC.py 

Possible capture modes: BX,L1A,linkreset_ROCt,linkreset_ROCd,linkreset_ECONt,linkreset_ECONd,orbitSync
"""

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE, NONE",default='NONE')
    parser.add_argument("--capture", dest="capture", type=str,
                        choices=["input","output"],
                        help="input or output capture?")
    parser.add_argument("--mode", dest="mode", type=str,
                        choices=["inmediate","BX","L1A","orbitSync","linkreset_ECONt","linkreset_ECONd","linkreset_ROCt","linkreset_ROCd"],help="capture mode")
    parser.add_argument("--fname",dest="fname", type=str,
                        default=None,help="filename to save captured data")
    parser.add_argument("--nwords",dest="nwords", type=int,
                        default=300,help="number of words to capture")
    
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

    logger = logging.getLogger('capture:ASIC')
    logger.setLevel(logging.INFO)

    lcapture = ""
    if args.capture=="input":
        lcapture = "ASIC-lc-input"
    elif args.capture=="output":
        lcapture = "ASIC-lc-output"
    else:
        logger.warning("not a valid lc")

    # configure lc
    nlinks = input_nlinks if args.capture=="input" else output_nlinks
    utils_lc.configure_acquire(dev,lcapture,args.mode,args.nwords,nlinks)
    # do an acquisition
    utils_lc.do_capture(dev,lcapture)
    # get data
    data = utils_lc.get_captured_data(dev,lcapture,args.nwords,nlinks)
    if args.fname is not None:
        utils_tv.save_testvector(capture+"-"+args.fname+".csv", data)
