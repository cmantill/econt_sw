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
   python testing/uhal-check_align.py 
"""

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE",default='INFO')
    parser.add_argument('--check', action='store_true', default=False, help='check that block is aligned')
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

    if args.check:
        if args.block=='from-IO':
            isIO_aligned = utils_io.check_IO(dev,io='from',nlinks=output_nlinks)
        elif args.block=='to-IO':
            isIO_aligned = utils_io.check_IO(dev,io='to',nlinks=output_nlinks)
        elif args.block=='lc-ASIC':
            is_lcASIC_aligned = utils_lc.check_links(dev,args.block,output_nlinks)

    else:
        if args.block=='from-IO':
            utils_io.print_IO(dev,io='from',nlinks=output_nlinks,io_name='IO')
            # check eye width
            for link in range(output_nlinks):
                delay_out = dev.getNode(names['IO']['from']+".link%i"%link+".reg3.delay_out").read()
                delay_out_N = dev.getNode(names['IO']['from']+".link%i"%link+".reg3.delay_out_N").read()
                dev.dispatch()
                logger.info("link %i: delay_out %i delay_out_N %i"%(link,delay_out,delay_out_N))
        elif args.block=='to-IO':
            utils_io.print_IO(dev,io='to',nlinks=output_nlinks,io_name='IO')
            for link in range(output_nlinks):
                delay_out = dev.getNode(names['IO']['to']+".link%i"%link+".reg3.delay_out").read()
                delay_out_N = dev.getNode(names['IO']['to']+".link%i"%link+".reg3.delay_out_N").read()
                dev.dispatch()
                logger.info("link %i: delay_out %i delay_out_N %i"%(link,delay_out,delay_out_N))

        elif args.block=='lc-ASIC':
            utils_lc.check_lc(dev,lcapture=args.block,nlinks=output_nlinks)

        elif args.block=='latency':
            latency_values = {}
            for lcapture in ['lc-ASIC','lc-emulator']:
                latency_values[lcapture] = []
                for l in range(output_nlinks):
                    latency = dev.getNode(names[lcapture]['lc']+".link"+str(l)+".fifo_latency").read();
                    dev.dispatch()
                    latency_values[lcapture].append(int(latency))
            logger.info('link-capture latency values %s'%latency_values)
