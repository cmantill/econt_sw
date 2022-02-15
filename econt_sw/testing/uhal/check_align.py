import uhal
import time
import argparse
import logging
logging.basicConfig()

from utils.uhal_config import *
import utils.link_capture as utils_lc
import utils.test_vectors as utils_tv
import utils.io as utils_io
import utils.fast_command as utils_fc

"""
Check alignment on tester

Usage:
   python testing/uhal-check_align.py --check --block [from-IO,to-IO,lc-ASIC,lc-emulator]
"""

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE",default='INFO')
    parser.add_argument('--check', action='store_true', default=False, help='check that block is aligned')
    parser.add_argument('--nlinks', type=int, default=-1, help='number of links')
    parser.add_argument('-B', '--block', dest='block', required=True)
    args = parser.parse_args()

    set_logLevel(args)
    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")

    logger = logging.getLogger('check-align')
    try:
        logger.setLevel(args.logLevel)
    except ValueError:
        logging.error("Invalid log level")
        exit(1)

    if args.nlinks==-1:
        nlinks = output_nlinks
    else:
        nlinks = args.nlinks

    if args.check:
        if args.block=='from-IO':
            # reset the counters!
            utils_io.reset_counters(dev,io='from')
            isIO_aligned = utils_io.check_IO(dev,'from',nlinks,verbose=False)
        elif args.block=='to-IO':
            # utils_io.reset_counters(dev,io='to')
            isIO_aligned = utils_io.check_IO(dev,'to',nlinks,verbose=False)
        elif args.block=='lc-ASIC':
            is_lcASIC_aligned = utils_lc.check_links(dev,args.block,nlinks)

    else:
        if args.block=='from-IO':
            utils_io.print_IO(dev,'from',nlinks)
            # check eye width
            utils_io.get_delay(dev,'from',nlinks,'IO',verbose=True)
        elif args.block=='to-IO':
            utils_io.print_IO(dev,'to',nlinks,'IO')
            utils_io.get_delay(dev,'to',nlinks,'IO',verbose=True)
        elif args.block=='lc-ASIC':
            utils_lc.check_lc(dev,lcapture=args.block,nlinks=nlinks)

        elif args.block=='latency':
            latency_values = {}
            for lcapture in ['lc-ASIC','lc-emulator']:
                latency_values[lcapture] = []
                for l in range(nlinks):
                    latency = dev.getNode(names[lcapture]['lc']+".link"+str(l)+".fifo_latency").read();
                    dev.dispatch()
                    latency_values[lcapture].append(int(latency))
            logger.info('link-capture latency values %s'%latency_values)
