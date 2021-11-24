import uhal
import time
import argparse
import numpy as np
import logging
logging.basicConfig()

from uhal_config import names,input_nlinks,output_nlinks
from uhal_utils import check_IO,check_links,configure_IO,get_captured_data,save_testvector,configure_acquire,do_fc_capture

"""
Alignment sequence on tester using python2 uhal.

Usage:
   python testing/uhal-findorb.py --delay 4
"""

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE, NONE",default='NONE')
    parser.add_argument('--delay', type=int, required=True, help="delay")
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

    logger = logging.getLogger('findorb')
    logger.setLevel(logging.INFO)
    
    # setup normal output in test-vectors
    out_brams = []
    testvectors_settings = {
        "output_select": 0x0,
        "n_idle_words": 255,
        "idle_word": 0xaccccccc,
        "idle_word_BX0": 0x9ccccccc,
        "header_mask": 0x00000000,
        "header": 0xa0000000,
        "header_BX0": 0x90000000,
    }
    
    for l in range(input_nlinks):
        for key,value in testvectors_settings.items():
            dev.getNode(names['testvectors']['switch']+".link"+str(l)+"."+key).write(value)            
        # size of bram is 4096
        out_brams.append([None] * 4095)
        dev.dispatch()

    # set zero-data with headers
    for l in range(input_nlinks):
        for i,b in enumerate(out_brams[l]):
            if i==0: 
                out_brams[l][i] = 0x90000000
            else:
                out_brams[l][i] = 0xa0000000
        dev.getNode(names['testvectors']['bram'].replace('00',"%02d"%l)).writeBlock(out_brams[l])
        dev.dispatch()
        time.sleep(0.001)

    # configure bypass
    for l in range(output_nlinks):
        dev.getNode(names['bypass']['switch']+".link"+str(l)+".output_select").write(0x1)
    dev.dispatch()
    
    # delay
    dev.getNode(names['delay']+".delay").write(args.delay)

    # configure fast command
    dev.getNode(names['fc']+".command.enable_fast_ctrl_stream").write(0x1);
    dev.getNode(names['fc']+".command.enable_orbit_sync").write(0x1);
    dev.getNode(names['fc']+".command.global_l1a_enable").write(0);

    # set BXs
    dev.getNode(names['fc']+".bx_link_reset_roct").write(3500)
    dev.getNode(names['fc']+".bx_link_reset_rocd").write(3501)
    dev.getNode(names['fc']+".bx_link_reset_econt").write(3502)
    dev.getNode(names['fc']+".bx_link_reset_econd").write(3503)
    
    # send link reset roct fast command
    # this will align the emulator on the ASIC board and the emulator on the tester board simultaneously
    lrc = dev.getNode(names['fc-recv']+".counters.link_reset_roct").read();
    dev.dispatch()
    logger.info('link reset roct counter %i'%lrc)
    
    dev.getNode(names['fc']+".request.link_reset_roct").write(0x1);
    dev.dispatch()
    time.sleep(0.001)
    
    lrc = dev.getNode(names['fc-recv']+".counters.link_reset_roct").read();
    dev.dispatch()
    logger.info('link reset roct counter %i'%lrc)
