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
    check_IO(dev,'to',nlinks=input_nlinks)
    
    # link captures
    lcapture_input = names["ASIC-lc-input"]
    lcapture_output = names["ASIC-lc-output"]

    # configure lc to capture on BX
    dev.getNode(lcapture_input["lc"]+".global.link_enable").write(0x1fff)
    dev.getNode(lcapture_input["lc"]+".global.explicit_resetb").write(0x0)
    time.sleep(0.001)
    dev.getNode(lcapture_input["lc"]+".global.explicit_resetb").write(0x1)
    dev.dispatch()
    for l in range(input_nlinks):
        dev.getNode(lcapture_input["lc"]+".link%i"%l+".L1A_offset_or_BX").write(0)
        dev.getNode(lcapture_input["lc"]+".link%i"%l+".capture_mode_in").write(0x1)
        dev.getNode(lcapture_input["lc"]+".link%i"%l+".aquire_length").write(300)
        dev.dispatch()

    # do an acquisition
    dev.getNode(lcapture_input["lc"]+".global.aquire").write(0)
    dev.getNode(lcapture_input["lc"]+".global.aquire").write(1)
    dev.dispatch()
    time.sleep(0.001)
    dev.getNode(lcapture_input["lc"]+".global.aquire").write(0)
    dev.dispatch()

    all_data = []
    all_data_filled=True
    for l in range(input_nlinks):
        fifo_occupancy = dev.getNode(lcapture_input["lc"]+".link%i"%l+".fifo_occupancy").read()
        dev.dispatch()
        if fifo_occupancy>0:
            data = dev.getNode(lcapture_input['fifo']+".link%i"%l).readBlock(int(fifo_occupancy))
            dev.dispatch()
            all_data.append(data)
        else:
            all_data_filled = False
            print('fifo occupancy %s %d' %(link,fifo_occupancy))
        dev.getNode(lcapture_input["lc"]+".link%i"%l+".aquire").write(0x0)
        dev.getNode(lcapture_input["lc"]+".link%i"%l+".explicit_rstb_acquire").write(0x0)
        dev.getNode(lcapture_input["lc"]+".link%i"%l+".explicit_rstb_acquire").write(0x1)
        dev.dispatch()
    dev.getNode(lcapture_input["lc"]+".global.interrupt_enable").write(0x0)
    dev.dispatch()
    # print data
    if all_data_filled:
        data = [[hex(all_data[j][i]) for j in range(len(all_data))] for i in range(len(all_data[0]))]
        for d in data[:10]:
            print(d)

    # configure link capture's align pattern
    dev.getNode(lcapture_input["lc"]+".global.link_enable").write(0x1fff)
    dev.getNode(lcapture_input["lc"]+".global.explicit_resetb").write(0x0)
    time.sleep(0.001)
    dev.getNode(lcapture_input["lc"]+".global.explicit_resetb").write(0x1)
    dev.dispatch()
    for l in range(input_nlinks):
        dev.getNode(lcapture_input["lc"]+".link%i"%l+".align_pattern").write(0xaccccccc)
        dev.getNode(lcapture_input["lc"]+".link%i"%l+".L1A_offset_or_BX").write(0)
        dev.getNode(lcapture_input["lc"]+".link%i"%l+".capture_mode_in").write(0x2)
        dev.getNode(lcapture_input["lc"]+".link%i"%l+".capture_linkreset_ROCt").write(0x1)
        dev.getNode(lcapture_input["lc"]+".link%i"%l+".capture_linkreset_ECONt").write(0x0)
        dev.getNode(lcapture_input["lc"]+".link%i"%l+".capture_L1A").write(0x0)
        dev.getNode(lcapture_input["lc"]+".link%i"%l+".capture_linkreset_ROCd").write(0x0)
        dev.getNode(lcapture_input["lc"]+".link%i"%l+".capture_linkreset_ECONd").write(0x0)
        dev.getNode(lcapture_input["lc"]+".link%i"%l+".aquire_length").write(300)
        dev.getNode(lcapture_input["lc"]+".link%i"%l+".fifo_latency").write(0x0)
        dev.dispatch()

    dev.getNode(lcapture_input["lc"]+".global.aquire").write(0)
    dev.getNode(lcapture_input["lc"]+".global.aquire").write(1)
    dev.dispatch()
    time.sleep(0.001)
    dev.getNode(lcapture_input["lc"]+".global.aquire").write(0)
    dev.dispatch()

    # read fast commands
    reset_roc = dev.getNode(names['ASIC-fc-recv']+".counters.link_reset_roct").read()
    dev.dispatch()
    reset_econt = dev.getNode(names['ASIC-fc-recv']+".counters.link_reset_econt").read()
    dev.dispatch()
    logger.info("Initial counters: reset roct %d, econt %d"%(reset_roc,reset_econt))
    raw_input("Link capture and counters checked. Waiting for link reset roct. Press key to continue...")

    reset_roc = dev.getNode(names['ASIC-fc-recv']+".counters.link_reset_roct").read()
    dev.dispatch()
    reset_econt = dev.getNode(names['ASIC-fc-recv']+".counters.link_reset_econt").read()
    dev.dispatch()
    logger.info("After counters: reset roct %d, econt %d"%(reset_roc,reset_econt))

    # check that lc is aligned
    for l in range(input_nlinks):
        aligned_c = dev.getNode(lcapture_input["lc"]+".link%i"%l+".link_aligned_count").read()
        error_c = dev.getNode(lcapture_input["lc"]+".link%i"%l+".link_error_count").read()
        aligned = dev.getNode(lcapture_input["lc"]+".link%i"%l+".status.link_aligned").read()
        delay_ready = dev.getNode(lcapture_input["lc"]+".link%i"%l+".status.delay_ready").read()
        waiting_for_trig = dev.getNode(lcapture_input["lc"]+".link%i"%l+".status.waiting_for_trig").read()
        writing =  dev.getNode(lcapture_input["lc"]+".link%i"%l+".status.writing").read()
        dev.dispatch()
        logger.info('input-link-capture link%i aligned: %d delayready: %d waiting: %d writing: %d aligned_c: %d error_c: %d'%(l, aligned, delay_ready, waiting_for_trig, writing, aligned_c, error_c))

    raw_input("Done with input link capture. Waiting to setup output link capture to acquire")

    # setup output capture to capture on link reset ECONT
    dev.getNode(lcapture_output['lc']+".global.link_enable").write(0x1fff)
    dev.getNode(lcapture_output['lc']+".global.explicit_resetb").write(0x0)
    time.sleep(0.001)
    dev.getNode(lcapture_output['lc']+".global.explicit_resetb").write(0x1)
    dev.dispatch()
    for l in range(output_nlinks):
        dev.getNode(lcapture_output['lc']+".link"+str(l)+".align_pattern").write(0b00100100010)
        dev.getNode(lcapture_output['lc']+".link"+str(l)+".L1A_offset_or_BX").write(0)
        
        dev.getNode(lcapture_output['lc']+".link"+str(l)+".capture_mode_in").write(0x2)
        dev.getNode(lcapture_output['lc']+".link"+str(l)+".capture_linkreset_ECONt").write(0x1)
        dev.getNode(lcapture_output['lc']+".link"+str(l)+".capture_L1A").write(0x0)
        dev.getNode(lcapture_output['lc']+".link"+str(l)+".capture_linkreset_ROCd").write(0x0)
        dev.getNode(lcapture_output['lc']+".link"+str(l)+".capture_linkreset_ROCt").write(0x0)
        dev.getNode(lcapture_output['lc']+".link"+str(l)+".capture_linkreset_ECONd").write(0x0)
        
        dev.getNode(lcapture_output['lc']+".link"+str(l)+".aquire_length").write(4096)
        dev.getNode(lcapture_output['lc']+".link"+str(l)+".fifo_latency").write(0)
        dev.dispatch()
    dev.getNode(lcapture_output['lc']+".global.aquire").write(0)
    dev.dispatch()
    dev.getNode(lcapture_output['lc']+".global.aquire").write(1)
    dev.dispatch()

    raw_input("Done with input link capture. Setup output link capture to acquire. Waiting to capture output after getting link reset ECONT.")

    # set acquire to 0
    dev.getNode(lcapture_output['lc']+".global.aquire").write(0)
    dev.dispatch()
    data = get_captured_data(dev,'ASIC-lc-output')
    save_testvector("lc-output-alignoutput_debug.csv", data)


