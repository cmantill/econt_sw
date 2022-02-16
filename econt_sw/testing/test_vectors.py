import uhal
import time
import argparse
import logging
logging.basicConfig()

from utils.uhal_config import *
import utils.link_capture as utils_lc
import utils.test_vectors as utils_tv

logger = logging.getLogger('input')

def configure_tv(dev,dtype,idir):
    utils_tv.set_testvectors(dev,dtype,idir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE",default='INFO')
    parser.add_argument('--dtype', type=str, default="", help='dytpe (PRBS32,PRBS,PRBS28,debug,zeros)')
    parser.add_argument('--idir',dest="idir",type=str, default="", help='test vector directory')
    
    args = parser.parse_args()

    set_logLevel(args)
    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")

    try:
        logger.setLevel(args.logLevel)
    except ValueError:
        logging.error("Invalid log level")
        exit(1)

    configure_tv(dev,args.dtype,args.idir)
