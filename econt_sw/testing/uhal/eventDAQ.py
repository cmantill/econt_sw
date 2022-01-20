import uhal
import time
import argparse
import os
import logging
logging.basicConfig()

from utils.uhal_config import *
import utils.stream_compare as utils_sc
import utils.fast_command as utils_fc
import utils.link_capture as utils_lc
import utils.io as utils_io
import utils.test_vectors as utils_tv

"""
Event DAQ using uHAL python2.

Usage:
   python testing/uhal-eventDAQ.py --idir INPUTDIR
"""

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE, NONE",default='NONE')
    parser.add_argument('--idir',dest="idir",type=str, help='test vector directory')
    parser.add_argument("--capture", dest="capture", type=str, help="capture data with one of the options", default=None)
    parser.add_argument('--compare',dest="compare",action='store_true', default=False, help='use stream compare')
    parser.add_argument('--stime',dest="stime",type=float, default=0.001, help='time between word counts')
    parser.add_argument('--nlinks',dest="nlinks",type=int, default=13, help='active links')
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

    logger = logging.getLogger('eventDAQ')
    logger.setLevel(logging.INFO)

    # make sure fc are configured
    utils_fc.configure_fc(dev)

    if args.idir:
        # setup test-vectors
        logger.info('set test vectors %s',args.idir)
        utils_tv.set_testvectors(dev,None,args.idir)

        # configure bypass to take data from test-vectors
        for l in range(output_nlinks):
            dev.getNode(names['bypass']['switch']+".link"+str(l)+".output_select").write(0x1)
        dev.dispatch()

    if args.compare:
        # setup stream compare
        utils_sc.compare(dev,args.nlinks,args.stime)
    
    if args.capture=='l1a' or args.capture=='trigger':
        # configure lc to capture on L1A 
        for lcapture in ['lc-input','lc-ASIC','lc-emulator']:
            nwords = 511 if 'input' in lcapture else 4095
            nlinks = input_nlinks if 'input' in lcapture else output_nlinks
            utils_lc.configure_acquire(dev,lcapture,"L1A",nwords,nlinks=nlinks)
            utils_lc.do_capture(dev,lcapture)

        if args.capture=='l1a':
            logger.info('Capture with l1a')
            capture = True
            l1a_counter = dev.getNode(names['fc-recv']+".counters.l1a").read()
            dev.dispatch()
            logger.debug('L1A counter %i'%(int(l1a_counter)))

            # send L1A
            utils_fc.send_l1a(dev)

        # get data
        all_data = {}
        for lcapture in ['lc-input','lc-ASIC','lc-emulator']:
            nlinks = input_nlinks if 'input' in lcapture else output_nlinks
            nwords = 511 if 'input' in lcapture else 4095
            if args.capture == "compare": nwords = 511
            all_data[lcapture] = utils_lc.get_captured_data(dev,lcapture,nwords,nlinks)

        # convert all data to format
        for key,data in all_data.items():
            fname = args.idir+"/%s-Output_header.csv"%key
            if args.capture == "compare":
                fname = fname.replace(".csv","_SC.csv")
            utils_tv.save_testvector( fname, data, header=True)

        # check link capture again
        # os.system('python testing/uhal/check_align.py --check -B lc-ASIC')

    # reset fc
    utils_fc.configure_fc(dev)
