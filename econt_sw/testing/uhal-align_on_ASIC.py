import uhal
import time
import argparse
import logging

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

    logger = logging.getLogger('align:ASIC:step:%s'%args.step)
    logger.setLevel(logging.INFO)

    names = {
        'IO': {'to': "IO-to-ECONT-IO-blocks-0",
               'from': "IO-from-ECONT-IO-blocks-0",
               },
        'lc-input': {'lc': "IO-to-ECONT-input-link-capture-link-capture-AXI-0",
                     'fifo': "IO-to-ECONT-input-link-capture-link-capture-AXI-0_FIFO",
                     },
        'lc-output': {'lc': "IO-from-ECONT-output-link-capture-link-capture-AXI-0",
                      'emulator': "IO-from-ECONT-output-link-capture-link-capture-AXI-0_FIFO",
                      },
        'fc-recv': "fast-command-fastcontrol-recv-axi-0",
    }

    input_nlinks = 12
    output_nlinks = 13

    # configure IO blocks
    for io,io_name in names['IO'].items():
        nlinks = input_nlinks if io=='to' else output_nlinks
        for l in range(nlinks):
            link = "link%i"%l
            dev.getNode(io_name+"."+link+".reg0.tristate_IOBUF").write(0x0)
            dev.getNode(io_name+"."+link+".reg0.bypass_IOBUF").write(0x0)
            dev.getNode(io_name+"."+link+".reg0.invert").write(0x0)
            
            dev.getNode(io_name+"."+link+".reg0.reset_link").write(0x0)
            dev.getNode(io_name+"."+link+".reg0.reset_counters").write(0x1)
            if io=='from':
                dev.getNode(io_name+"."+link+".reg0.delay_mode").write(0x0)
            else:
                dev.getNode(io_name+"."+link+".reg0.delay_mode").write(0x1)
        dev.getNode(io_name+".global.global_rstb_links").write(0x1)
        dev.dispatch()

    raw_input("IO blocks configured. Waiting for bit transitions. Press key to continue...")

    # check that to-IO is aligned
    for l in range(input_nlinks):
        while True:
            link = "link%i"%l
            bit_tr = dev.getNode(names['IO']['to']+"."+link+".reg3.waiting_for_transitions").read()
            delay_ready = dev.getNode(names['IO']['to']+"."+link+".reg3.delay_ready").read()
            dev.dispatch()
            logger.info("%s: bit_tr %d and delay ready %d"%(link,bit_tr,delay_ready))
            if delay_ready==1:
                break;    

    # configure link capture 
    dev.getNode(names["lc-input"]["lc"]+".global.link_enable").write(0x1fff)
    dev.getNode(names["lc-input"]["lc"]+".global.explicit_resetb").write(0x0)
    time.sleep(0.001)
    dev.getNode(names["lc-input"]["lc"]+".global.explicit_resetb").write(0x1)
    dev.dispatch()
    # capture on BX
    for l in range(input_nlinks):
        link = "link%i"%l
        dev.getNode(names["lc-input"]["lc"]+"."+link+".align_pattern").write(0b00100100010)
        dev.getNode(names["lc-input"]["lc"]+"."+link+".L1A_offset_or_BX").write(3500)
        dev.getNode(names["lc-input"]["lc"]+"."+link+".capture_mode_in").write(0x1)
        dev.getNode(names["lc-input"]["lc"]+"."+link+".aquire_length").write(0x1000)
        dev.getNode(names["lc-input"]["lc"]+"."+link+".fifo_latency").write(0x0)
        dev.dispatch()
    dev.getNode(names["lc-input"]["lc"]+".global.aquire").write(0)
    dev.getNode(names["lc-input"]["lc"]+".global.aquire").write(1)
    dev.dispatch()
    time.sleep(0.001)
    dev.getNode(names["lc-input"]["lc"]+".global.aquire").write(0)
    dev.dispatch()

    for l in range(input_nlinks):
        link = "link%i"%l
        aligned_c = dev.getNode(names["lc-input"]["lc"]+"."+link+".link_aligned_count").read()
        error_c = dev.getNode(names["lc-input"]["lc"]+"."+link+".link_error_count").read()
        aligned = dev.getNode(names["lc-input"]["lc"]+"."+link+".status.link_aligned").read()
        dev.dispatch()
        logger.info('input-link-capture %s %d %d %d'%(link, aligned, aligned_c, error_c))

        fifo_occupancy = dev.getNode(names["lc-input"]["lc"]+"."+link+".fifo_occupancy").read()
        dev.dispatch()
        if fifo_occupancy>0:
            data = dev.getNode(input_bram_name+"."+link).readBlock(int(fifo_occupancy))
            dev.dispatch()
            print('fifo occupancy %s %d %i' %(link,fifo_occupancy,len(data)))
            if l==0:
                print(link)
                print([hex(d) for i,d in enumerate(data) if i<15])
        dev.getNode(names["lc-input"]["lc"]+"."+link+".aquire").write(0x0)
        dev.getNode(names["lc-input"]["lc"]+"."+link+".explicit_rstb_acquire").write(0x0)
        dev.getNode(names["lc-input"]["lc"]+"."+link+".explicit_rstb_acquire").write(0x1)
        dev.dispatch()
    dev.getNode(names["lc-input"]["lc"]+".global.interrupt_enable").write(0x0)
    dev.dispatch()


    # read fast commands
    reset_roc = dev.getNode(names['fc-recv']+".counters.link_reset_roct").read()
    dev.dispatch()
    reset_econt = dev.getNode(names['fc-recv']+".counters.link_reset_econt").read()
    dev.dispatch()
    logger.info("Initial counters: reset roct %d, econt %d"%(reset_roc,reset_econt))
    raw_input("Link capture and counters checked. Waiting for link reset roct. Press key to continue...")

    # read again
    reset_roc = dev.getNode(names['fc-recv']+".counters.link_reset_roct").read()
    dev.dispatch()
    reset_econt = dev.getNode(names['fc-recv']+".counters.link_reset_econt").read()
    dev.dispatch()
    logger.info("After counters: reset roct %d, econt %d"%(reset_roc,reset_econt))

    # check if input link capture is aligned
    for l in range(input_nlinks):
        link = "link%i"%l
        aligned_c = dev.getNode(names["lc-input"]["lc"]+"."+link+".link_aligned_count").read()
        error_c = dev.getNode(names["lc-input"]["lc"]+"."+link+".link_error_count").read()
        aligned = dev.getNode(names["lc-input"]["lc"]+"."+link+".status.link_aligned").read()
        dev.dispatch()
        print('%s %s %d %d %d'%(names["lc-input"]["lc"],link, aligned, aligned_c, error_c))

        fifo_occupancy = dev.getNode(names["lc-input"]["lc"]+"."+link+".fifo_occupancy").read()
        dev.dispatch()
        if fifo_occupancy>0:
            data = dev.getNode(input_bram_name+"."+link).readBlock(int(fifo_occupancy))
            dev.dispatch()
            print('fifo occupancy %s %d %i' %(link,fifo_occupancy,len(data)))
            if l==0:
                print(link)
                print([hex(i) for i in data])
        dev.getNode(names["lc-input"]["lc"]+"."+link+".aquire").write(0x0)
        dev.getNode(names["lc-input"]["lc"]+"."+link+".explicit_rstb_acquire").write(0x0)
        dev.getNode(names["lc-input"]["lc"]+"."+link+".explicit_rstb_acquire").write(0x1)
        dev.dispatch()
    dev.getNode(names["lc-input"]["lc"]+".global.interrupt_enable").write(0x0)
    dev.dispatch()
