import uhal
import time
import argparse
import numpy
import logging

logging.basicConfig()

"""
Alignment sequence on tester using python2 uhal.

Usage:
   python testing/uhal-align_on_tester.py --step [tester-phase,asic-word,asic-tester]
"""

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE, NONE",default='NONE')
    parser.add_argument('--step', choices=['tester-phase','asic-word','asic-tester'], help='alignment steps')
    
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

    logger = logging.getLogger('align:step:%s'%args.step)
    logger.setLevel(logging.INFO)
    
    names = {
        'IO': {'to': "ASIC-IO-IO-to-ECONT-ASIC-IO-blocks-0",
               'from': "ASIC-IO-IO-from-ECONT-ASIC-IO-blocks-0"},
        'testvectors': {'switch': "test-vectors-to-ASIC-and-emulator-test-vectors-ipif-switch-mux",
                        'stream': "test-vectors-to-ASIC-and-emulator-test-vectors-ipif-stream-mux",
                        'bram': "test-vectors-to-ASIC-and-emulator-test-vectors-out-block00-bram-ctrl"
                    },
        'bypass': {'switch': "econt-emulator-bypass-option-expected-outputs-RAM-ipif-switch-mux",
                   'stream': "econt-emulator-bypass-option-expected-outputs-RAM-ipif-stream-mux"
               },
        'fc': "housekeeping-FastControl-fastcontrol-axi-0",
        'fc-recv': "housekeeping-FastControl-fastcontrol-recv-axi-0",
        'lc-ASIC': {'lc': "capture-align-compare-ECONT-ASIC-link-capture-link-capture-AXI-0",
                    'fifo': "capture-align-compare-ECONT-ASIC-link-capture-link-capture-AXI-0_FIFO",
                    },
        'lc-emulator': {'lc': "capture-align-compare-ECONT-emulator-link-capture-link-capture-AXI-0",
                        'fifo': "capture-align-compare-ECONT-emulator-link-capture-link-capture-AXI-0_FIFO",
                        },
        'stream_compare': "capture-align-compare-compare-outputs-stream-compare-0",

    }
    input_nlinks = 12
    output_nlinks = 13

    if args.step == "tester-phase":
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
                if io=='to':
                    dev.getNode(io_name+"."+link+".reg0.delay_mode").write(0x0)
                else:
                    dev.getNode(io_name+"."+link+".reg0.delay_mode").write(0x1)
            dev.getNode(io_name+".global.global_rstb_links").write(0x1)
            dev.dispatch()
        
        # send PRBS
        for l in range(input_nlinks):
            link = "link%i"%l
            dev.getNode(names['testvectors']['switch']+"."+link+".output_select").write(0x1)
        dev.dispatch()
        raw_input("IO blocks configured. Sending PRBS. Press key to continue...")

        # check that from-IO is aligned
        for l in range(output_nlinks):
            while True:
                link = "link%i"%l
                bit_tr = dev.getNode(names['IO']['from']+"."+link+".reg3.waiting_for_transitions").read()
                delay_ready = dev.getNode(names['IO']['from']+"."+link+".reg3.delay_ready").read()
                dev.dispatch()
                logger.debug("from-IO %s: bit_tr %d and delay ready %d"%(link,bit_tr,delay_ready))
                if delay_ready==1:
                    break

    if args.step == "asic-word":
        # setup normal output in test-vectors
        out_brams = []
        testvectors_settings = {"output_select": 0x0,
                                "n_idle_words": 255,
                                # "n_idle_words":	0,
                                "idle_word": 0xaccccccc,
                                "idle_word_BX0": 0x9ccccccc,
                                "header_mask": 0xf0000000,
                                # "header_mask": 0x00000000,
                                "header": 0xa0000000,
                                "header_BX0": 0x90000000,
                                }
                                
        for l in range(input_nlinks):
            link = "link%i"%l
            for key,value in testvectors_settings.items():
                dev.getNode(names['testvectors']['switch']+"."+link+"."+key).write(value)
            
            # size of bram is 4096
            out_brams.append([None] * 4096)
            
            dev.getNode(names['testvectors']['stream']+"."+link+".sync_mode").write(0x1)
            dev.getNode(names['testvectors']['stream']+"."+link+".ram_range").write(0x1)
            dev.getNode(names['testvectors']['stream']+"."+link+".force_sync").write(0x0)
        dev.dispatch()

        # set zero-data with headers
        for l in range(input_nlinks):
            for i,b in enumerate(out_brams[l]):
                if i==0: out_brams[l][i] = 0x90000000
                else:
                    out_brams[l][i] = 0xa0000000
                    #out_brams[l][i] = 0xa0000000+i
            dev.getNode(names['testvectors']['bram'].replace('00',"%02d"%l)).writeBlock(out_brams[l])
            dev.dispatch()
            time.sleep(0.001)

        # configure bypass
        for l in range(output_nlinks):
            link = "link%i"%l
            dev.getNode(names['bypass']['switch']+"."+link+".output_select").write(0x1)
        dev.dispatch()

        # configure fast command
        dev.getNode(names['fc']+".command.enable_fast_ctrl_stream").write(0x1);
        dev.getNode(names['fc']+".command.enable_orbit_sync").write(0x1);
        
        # set BXs
        dev.getNode(names['fc']+".bx_link_reset_roct").write(3500)
        dev.getNode(names['fc']+".bx_link_reset_rocd").write(3501)
        dev.getNode(names['fc']+".bx_link_reset_econt").write(3502)
        dev.getNode(names['fc']+".bx_link_reset_econd").write(3503)

        # send link reset roct
        # this would align the emulator on the ASIC board and the emulator on the tester board simultaneously
        dev.getNode(names['fc']+".request.link_reset_roct").write(0x1);
        raw_input("Sent link reset ROCT. Press key to continue...")

    if args.step == "asic-tester":
        # configure link captures
        for lcapture in [names['lc-ASIC'],names['lc-emulator']]:
            lcapture = lcapture['lc']
            dev.getNode(lcapture+".global.link_enable").write(0x1fff)
            dev.getNode(lcapture+".global.explicit_resetb").write(0x0)
            time.sleep(0.001)
            dev.getNode(lcapture+".global.explicit_resetb").write(0x1)
            dev.dispatch()
            for l in range(output_nlinks):
                link = "link%i"%l
                dev.getNode(lcapture+"."+link+".align_pattern").write(0b00100100010)
                dev.getNode(lcapture+"."+link+".L1A_offset_or_BX").write(0)

                # set lc to capture on link reset ECONT
                dev.getNode(lcapture+"."+link+".capture_mode_in").write(0x2)
                dev.getNode(lcapture+"."+link+".capture_linkreset_ECONt").write(0x1)
                dev.getNode(lcapture+"."+link+".capture_L1A").write(0x0)
                dev.getNode(lcapture+"."+link+".capture_linkreset_ROCd").write(0x0)
                dev.getNode(lcapture+"."+link+".capture_linkreset_ROCt").write(0x0)
                dev.getNode(lcapture+"."+link+".capture_linkreset_ECONd").write(0x0)
                
                dev.getNode(lcapture+"."+link+".aquire_length").write(4096)
                dev.getNode(lcapture+"."+link+".fifo_latency").write(0);
            dev.dispatch()

        # send link reset roct (once)
        lrc = dev.getNode(names['fc-recv']+".counters.link_reset_econt").read();
        dev.dispatch()
        dev.getNode(names['fc']+".bx_link_reset_econt").write(3550)
        dev.dispatch()
        logger.info('link reset econt counter %i'%lrc)
        dev.getNode(names['fc']+".request.link_reset_econt").write(0x1);
        dev.dispatch()
        lrc = dev.getNode(names['fc-recv']+".counters.link_reset_econt").read();
        dev.dispatch()
        logger.info('link reset econt counter %i'%lrc)
        
        def find_latency(latency):
            # adjust latency
            new_latency = {}
            for l in range(output_nlinks):
                dev.getNode(names['lc-ASIC']['lc']+".fifo_latency").write(latency[l]);
            dev.dispatch()

            # do capture
            dev.getNode(names['lc-ASIC']['lc']+".global.aquire").write(0)
            dev.getNode(names['lc-emulator']['lc']+".global.aquire").write(0)
            dev.dispatch()
            dev.getNode(names['lc-ASIC']['lc']+".global.aquire").write(1)
            dev.getNode(names['lc-emulator']['lc']+".global.aquire").write(1)
            dev.dispatch()
            dev.getNode(names['lc-ASIC']['lc']+".global.aquire").write(0)
            dev.getNode(names['lc-emulator']['lc']+".global.aquire").write(0)
            dev.dispatch()

            # check link capture ASIC
            for l in range(output_nlinks):
                link = "link%i"%l
                aligned_c = dev.getNode(names['lc-ASIC']['lc']+"."+link+".link_aligned_count").read()
                error_c = dev.getNode(names['lc-ASIC']['lc']+"."+link+".link_error_count").read()
                aligned = dev.getNode(names['lc-ASIC']['lc']+"."+link+".status.link_aligned").read()
                dev.dispatch()
                asic_i = -1;
                if(aligned_c==128 and error_c==0 and aligned==1):
                    logger.info('%i: ASIC link-capture %s aligned: %d %d %d'%(latency[l],link, aligned, aligned_c, error_c))
                else:
                    # logger.warning('ASIC link-capture %s not aligned: : %d %d %d'%(link, aligned, aligned_c, error_c))
                    new_latency[l] = -1
                    continue
                fifo_occupancy = dev.getNode(names['lc-ASIC']['lc']+"."+link+".fifo_occupancy").read()
                dev.dispatch()
                occ = '%d'%fifo_occupancy
                if occ>0:
                    data = dev.getNode(names['lc-ASIC']['fifo']+"."+link).readBlock(int(fifo_occupancy))
                    dev.dispatch()
                    # logger.info('ASIC link-capture fifo occupancy %s %d %i' %(link,fifo_occupancy,len(data)))
                    for i,d in enumerate(data):
                        if d==0xf922f922:
                            asic_i = i
                            break;
                if(asic_i>-1):
                    logger.info('%i ASIC link-capture found BX0 word at %d',latency[l],asic_i)
                    new_latency[l] = latency[l]
                else:
                    #logger.warning('ASIC link-capture did not find BX0 word')
                    new_latency[l] = -1
                    
            return new_latency

        latency = {}
        for l in range(output_nlinks):
	    latency[l] = -1
            
        for i in range(0,1):
            for l in range(output_nlinks):
                if latency[l]==-1: 
                    latency[l] = i
            latency = find_latency(latency)

        print(latency)
        """
        # relative align
        def relative_align(fifo_latency):
            found_latency = False
            logger.info('Relative alignment')

            # set latency
            for l in range(output_nlinks):
                link = "link%i"%l
                dev.getNode(names['lc-ASIC']['lc']+"."+link+".fifo_latency").write(1)
                dev.getNode(names['lc-emulator']['lc']+"."+link+".fifo_latency").write(fifo_latency)
            dev.dispatch()
                
            # write global acquire
            dev.getNode(names['lc-ASIC']['lc']+".global.aquire").write(0)
            dev.getNode(names['lc-emulator']['lc']+".global.aquire").write(0)
            dev.dispatch()
            dev.getNode(names['lc-ASIC']['lc']+".global.aquire").write(1)
            dev.getNode(names['lc-emulator']['lc']+".global.aquire").write(1)
            dev.dispatch()
            
            # send link reset ECONT
            dev.getNode(names['fc']+".bx_link_reset_econt").write(3550) 
            dev.dispatch()
            dev.getNode(names['fc']+".request.link_reset_econt").write(0x1);
            dev.dispatch()
            
            # reset global acquire
            dev.getNode(names['lc-ASIC']['lc']+".global.aquire").write(0)
            dev.getNode(names['lc-emulator']['lc']+".global.aquire").write(0)
            dev.dispatch()

            # check link reset ECONT counter
            lrc = dev.getNode(names['fc-recv']+".counters.link_reset_econt").read();
            dev.dispatch()
            logger.info('link reset econt counter %i'%lrc)

            # check if link capture ASIC is aligned
            asic_i = 0
            for l in range(output_nlinks):
                link = "link%i"%l
                aligned_c = dev.getNode(names['lc-ASIC']['lc']+"."+link+".link_aligned_count").read()
                error_c = dev.getNode(names['lc-ASIC']['lc']+"."+link+".link_error_count").read()
                aligned = dev.getNode(names['lc-ASIC']['lc']+"."+link+".status.link_aligned").read()
                dev.dispatch()
                logger.info('ASIC link-capture %s aligned: %d %d %d'%(link, aligned, aligned_c, error_c))
                
                fifo_occupancy = dev.getNode(names['lc-ASIC']['lc']+"."+link+".fifo_occupancy").read()
                dev.dispatch()
                occ = '%d'%fifo_occupancy
                if occ>0:
                    data = dev.getNode(names['lc-ASIC']['fifo']+"."+link).readBlock(int(fifo_occupancy))
                    dev.dispatch()
                    logger.info('ASIC link-capture fifo occupancy %s %d %i' %(link,fifo_occupancy,len(data)))
                    if l==0:
                        for i,d in enumerate(data):
                            if d==0xf922f922:
                                print(i,hex(d))
                                asic_i = i
                                break;
            dev.getNode(names['lc-ASIC']['lc']+".global.interrupt_enable").write(0x0)
            dev.dispatch()

            # check if link capture Emulator is aligned
            for l in range(output_nlinks):
                link = "link%i"%l
                aligned_c = dev.getNode(names['lc-emulator']['lc']+"."+link+".link_aligned_count").read()
                error_c = dev.getNode(names['lc-emulator']['lc']+"."+link+".link_error_count").read()
                aligned = dev.getNode(names['lc-emulator']['lc']+"."+link+".status.link_aligned").read()
                dev.dispatch()
                logger.info('Emulator link-capture %s aligned: %d %d %d'%(link, aligned, aligned_c, error_c))
                
                fifo_occupancy = dev.getNode(names['lc-emulator']['lc']+"."+link+".fifo_occupancy").read()
                dev.dispatch()
                occ = '%d'%fifo_occupancy
                if occ>0:
                    data = dev.getNode(names['lc-emulator']['fifo']+"."+link).readBlock(int(fifo_occupancy))
                    dev.dispatch()
                    logger.debug('Emulator fifo occupancy  %s %d %i' %(link,fifo_occupancy,len(data)))
                    if l==0:
                        for i,d in enumerate(data):
                            if d==0xf922f922:
                                print(i,hex(d))
                                if i==asic_i:
                                    found_latency = True
                dev.getNode(names['lc-emulator']['lc']+"."+link+".aquire").write(0x0)
                dev.getNode(names['lc-emulator']['lc']+"."+link+".explicit_rstb_acquire").write(0x0)
                dev.getNode(names['lc-emulator']['lc']+"."+link+".explicit_rstb_acquire").write(0x1)
                dev.dispatch()
            dev.getNode(names['lc-emulator']['lc']+".global.interrupt_enable").write(0x0)
            dev.dispatch()
            return found_latency

        # iterate over different fifo latencies
        for lat in range(0,15):
            ret = relative_align(lat)
            if ret:
                print('found!')
                break;

        # test stream-compare as extra
        dev.getNode(names['stream_compare']+".control.reset").write(0x1) # start the counters from zero
        time.sleep(0.001)
        dev.getNode(names['stream_compare']+".control.latch").write(0x1)
        dev.dispatch()
        word_count = dev.getNode(names['stream_compare']+".word_count").read()
        err_count = dev.getNode(names['stream_compare']+".err_count").read()
        dev.dispatch()
        logger.info('Stream compare, word count %d, error count %d'%(word_count,err_count))

        # send a L1A to two capture blocks
        # dev.getNode(names['stream_compare']+".trigger").write(0x1)
        # then set the capture blocks to capture when they see a L1A
        """
