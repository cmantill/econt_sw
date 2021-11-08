import uhal
import time
import argparse
import logging
logging.basicConfig()

from uhal_config import names,input_nlinks,output_nlinks
from uhal_utils import get_captured_data,save_testvector,configure_IO,check_IO

"""
Alignment sequence on 'ASIC' - (emulator) using python2 uhal.

Usage:
   python testing/uhal-align_on_ASIC.py 
"""

# capture input data
# possible capture modes: BX,L1A,linkreset_ROCt,linkreset_ROCd,linkreset_ECONt,linkreset_ECONd,orbitSync
def getInputData(mode="linkreset_ROCt",nwords=300):
    # capture lc
    configure_acquire(dev,"ASIC-lc-input",mode,nwords,input_nlinks)
    # do an acquisition
    do_capture(dev,"ASIC-lc-input")
    # get input data
    input_data = get_captured_data(dev,"ASIC-lc-input",nwords,input_nlinks)
    return input_data

# capture output data
def getOutputData(mode="linkreset_ECONt",nwords=4095):
    # capture lc
    configure_acquire(dev,"ASIC-lc-output",mode,nwords,output_nlinks)
    # do an acquisition
    do_capture(dev,"ASIC-lc-output")
    # get output data
    output_data = get_captured_data(dev,"ASIC-lc-output",nwords,output_nlinks)
    return output_data

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

    if args.capture=="input":
        data = getInputData(args.mode,args.nwords)
        if args.fname is not None:
            save_testvector("lc-input"+args.fname+".csv", data)

    if args.capture=="output":
        data = getOutputData(args.mode,args.nwords)
        if args.fname is not None:
            save_testvector("lc-output"+args.fname+".csv", data)


