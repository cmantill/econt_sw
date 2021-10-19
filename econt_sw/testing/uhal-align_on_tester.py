import uhal
import time
import argparse
import numpy as np
import logging
logging.basicConfig()

from uhal_config import names,input_nlinks,output_nlinks
from uhal_utils import get_captured_data,save_testvector

"""
Alignment sequence on tester using python2 uhal.

Usage:
   python testing/uhal-align_on_tester.py --step [tester-phase,asic-word,asic-tester]
"""

"""
Find if with that latency we see the BX0 word.
If `bx0[l]` is set, then check that that position at which BX0 word is found, is the same as bx0.
"""
def find_latency(latency,lcapture,bx0=None):
    # record the new latency for each elink
    new_latency = {}
    # record the poisition at which BX0 was found for each elink
    found_BX0 = {}

    # set latency
    for l in range(output_nlinks):
        dev.getNode(names[lcapture]['lc']+".link"+str(l)+".fifo_latency").write(latency[l]);
    dev.dispatch()

    # do one capture on link reset
    dev.getNode(names[lcapture]['lc']+".global.aquire").write(0)
    dev.dispatch()
    dev.getNode(names[lcapture]['lc']+".global.aquire").write(1)
    dev.dispatch()
    dev.getNode(names['fc']+".request.link_reset_econt").write(0x1);
    dev.dispatch()
    dev.getNode(names[lcapture]['lc']+".global.aquire").write(0)
    dev.dispatch()
    
    # wait some time till acquisition has finished
    while True:
        fifo_occupancies = []
        for l in range(output_nlinks):
            fifo_occupancy = dev.getNode(names[lcapture]['lc']+".link"+str(l)+".fifo_occupancy").read()
            dev.dispatch()
            fifo_occupancies.append(int(fifo_occupancy))
        try:
            assert(np.all(np.array(fifo_occupancies) == fifo_occupancies[0]))
            break
        except:
            continue

    # check link reset econt counter
    #lrc = dev.getNode(names['fc-recv']+".counters.link_reset_econt").read();
    #dev.dispatch()
    #logger.info('link reset econt counter %i'%lrc)

    # data to be saved (for debug)
    daq_data = []

    # check link capture 
    for l in range(output_nlinks):
        # look at fifo
        fifo_occupancy = dev.getNode(names[lcapture]['lc']+".link"+str(l)+".fifo_occupancy").read()
        dev.dispatch()

        if int(fifo_occupancy)>0:
            # position at which bx0 is found for each link 
            bx0_i = -1;
            
            # retrieve data
            data = dev.getNode(names[lcapture]['fifo']+".link%i"%l).readBlock(int(fifo_occupancy))
            dev.dispatch()
            logger.debug('%s fifo occupancy link%i %d %i' %(lcapture,l,fifo_occupancy,len(data)))

            # look for BX0 word
            for i,d in enumerate(data):
                if d==0xf922f922:
                    bx0_i = i
                    break;
                    
            found_bx0 = False
            if bx0:
                if bx0[l]==bx0_i:
                    found_bx0=True
            else:
                found_bx0 =True
                    
            # if BX0 word is found then set the latency for that elink and save the data
            if(bx0_i>-1 and found_bx0):
                logger.debug('Latency %i: %s found BX0 word at %d',latency[l],lcapture,bx0_i)
                new_latency[l] = latency[l]
                found_BX0[l] = bx0_i
                daq_data.append([int(d) for d in data])
            else:
                # print(bx0_i,found_bx0)
                logger.warning('%s did not find BX0 word for link%i'%(lcapture,l))
                new_latency[l] = -1
        else:
            logger.warning('No captured data for ASIC')

        fifo_occupancy = dev.getNode(names[lcapture]['lc']+".link"+str(l)+".fifo_occupancy").read()
        dev.dispatch()
    return new_latency,found_BX0,np.array(daq_data).T
        
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
    
    if args.step == "tester-phase":
        # configure IO blocks
        for io,io_name in names['IO'].items():
            nlinks = input_nlinks if io=='to' else output_nlinks
            for l in range(nlinks):
                dev.getNode(io_name+".link"+str(l)+".reg0.tristate_IOBUF").write(0x0)
                dev.getNode(io_name+".link"+str(l)+".reg0.bypass_IOBUF").write(0x0)
                dev.getNode(io_name+".link"+str(l)+".reg0.invert").write(0x0)
                dev.getNode(io_name+".link"+str(l)+".reg0.reset_link").write(0x0)
                dev.getNode(io_name+".link"+str(l)+".reg0.reset_counters").write(0x1)
                if io=='to':
                    dev.getNode(io_name+".link"+str(l)+".reg0.delay_mode").write(0x0)
                else:
                    dev.getNode(io_name+".link"+str(l)+".reg0.delay_mode").write(0x1)
            dev.getNode(io_name+".global.global_rstb_links").write(0x1)
            dev.dispatch()
        
        # send PRBS
        testvectors_settings = {
            "output_select": 0x1,
            "n_idle_words": 256,
            "idle_word": 0xaccccccc,
            "idle_word_BX0": 0x9ccccccc,
            "header_mask": 0xf0000000, # impose headers
            "header": 0xa0000000,
            "header_BX0": 0x90000000,
        }
        for l in range(input_nlinks):
            for key,value in testvectors_settings.items():
                dev.getNode(names['testvectors']['switch']+".link"+str(l)+"."+key).write(value)
            dev.getNode(names['testvectors']['stream']+".link"+str(l)+".sync_mode").write(0x1)
            dev.getNode(names['testvectors']['stream']+".link"+str(l)+".ram_range").write(0x1)
            dev.getNode(names['testvectors']['stream']+".link"+str(l)+".force_sync").write(0x0)
        dev.dispatch()
        raw_input("IO blocks configured. Sending PRBS. Press key to continue...")

        # check that from-IO is aligned
        for l in range(output_nlinks):
            while True:
                bit_tr = dev.getNode(names['IO']['from']+".link"+str(l)+".reg3.waiting_for_transitions").read()
                delay_ready = dev.getNode(names['IO']['from']+".link"+str(l)+".reg3.delay_ready").read()
                dev.dispatch()
                logger.debug("from-IO link%i: bit_tr %d and delay ready %d"%(l,bit_tr,delay_ready))
                if delay_ready==1:
                    break
        logger.info("from-IO aligned")

    if args.step == "asic-word":
        # setup normal output in test-vectors
        out_brams = []
        testvectors_settings = {"output_select": 0x0,
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
            out_brams.append([None] * 4096)
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

        # configure fast command
        dev.getNode(names['fc']+".command.enable_fast_ctrl_stream").write(0x1);
        dev.getNode(names['fc']+".command.enable_orbit_sync").write(0x1);
        dev.getNode(names['fc']+".command.global_l1a_enable").write(0);

        # set BXs
        dev.getNode(names['fc']+".bx_link_reset_roct").write(3500)
        dev.getNode(names['fc']+".bx_link_reset_rocd").write(3501)
        dev.getNode(names['fc']+".bx_link_reset_econt").write(3502)
        dev.getNode(names['fc']+".bx_link_reset_econd").write(3503)
        
        # send link reset roct 
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

        raw_input("Sent link reset ROCT. Press key to continue...")

    if args.step == "asic-tester":
        # configure link captures
        for lcapture in ['lc-ASIC','lc-emulator']:
            dev.getNode(names[lcapture]['lc']+".global.link_enable").write(0x1fff)
            dev.getNode(names[lcapture]['lc']+".global.explicit_resetb").write(0x0)
            time.sleep(0.001)
            dev.getNode(names[lcapture]['lc']+".global.explicit_resetb").write(0x1)
            dev.dispatch()
            for l in range(output_nlinks):
                dev.getNode(names[lcapture]['lc']+".link"+str(l)+".align_pattern").write(0b00100100010)
                dev.getNode(names[lcapture]['lc']+".link"+str(l)+".L1A_offset_or_BX").write(0)

                # set lc to capture on link reset ECONT
                dev.getNode(names[lcapture]['lc']+".link"+str(l)+".capture_mode_in").write(0x2)
                dev.getNode(names[lcapture]['lc']+".link"+str(l)+".capture_linkreset_ECONt").write(0x1)
                dev.getNode(names[lcapture]['lc']+".link"+str(l)+".capture_L1A").write(0x0)
                dev.getNode(names[lcapture]['lc']+".link"+str(l)+".capture_linkreset_ROCd").write(0x0)
                dev.getNode(names[lcapture]['lc']+".link"+str(l)+".capture_linkreset_ROCt").write(0x0)
                dev.getNode(names[lcapture]['lc']+".link"+str(l)+".capture_linkreset_ECONd").write(0x0)
                
                dev.getNode(names[lcapture]['lc']+".link"+str(l)+".aquire_length").write(4096)
                dev.getNode(names[lcapture]['lc']+".link"+str(l)+".fifo_latency").write(0);
            dev.dispatch()

        # send link reset econt (once)
        lrc = dev.getNode(names['fc-recv']+".counters.link_reset_econt").read();
        dev.dispatch()
        dev.getNode(names['fc']+".bx_link_reset_econt").write(3550)
        dev.dispatch()
        logger.info('link reset econt counter %i'%lrc)
        dev.getNode(names['fc']+".request.link_reset_econt").write(0x1);
        dev.dispatch()
        time.sleep(0.001)
        lrc = dev.getNode(names['fc-recv']+".counters.link_reset_econt").read();
        dev.dispatch()
        logger.info('link reset econt counter %i'%lrc)

        # check links
        lc_align = []
        for l in range(output_nlinks):
            aligned_c = dev.getNode(names['lc-ASIC']['lc']+".link"+str(l)+".link_aligned_count").read()
            error_c = dev.getNode(names['lc-ASIC']['lc']+".link"+str(l)+".link_error_count").read()
            aligned = dev.getNode(names['lc-ASIC']['lc']+".link"+str(l)+".status.link_aligned").read()
            dev.dispatch()
            lc_align.append((aligned_c,error_c,aligned))
        aligned_counter = np.array([int(lc_align[i][0]) for i in range(len(lc_align))])
        error_counter = np.array([int(lc_align[i][1]) for i in range(len(lc_align))])
        is_aligned = np.array([int(lc_align[i][2]) for i in range(len(lc_align))])
        # print(is_aligned,error_counter,aligned_counter)
        try:
            assert np.all(is_aligned==1)
            assert np.all(aligned_counter==128)
            assert np.all(error_counter==0)
            logger.info('ASIC link-capture all links are aligned')
        except AssertionError:
            logger.error('ASIC link-capture is not aligned:')
            for i in range(len(lc_align)):
                logger.error('LINK-%i: %d %d %d'%(i, is_aligned[i], aligned_counter[i], error_counter[i]))

        # data to be captured
        all_data = {}
                
        # set fifo latency for lc-ASIC
        # initiate dictionary with default values of latency
        latency_asic = {}
        for l in range(output_nlinks):
	    latency_asic[l] = -1

        asic_found = {}
        for i in range(0,511): # max fifo latency?
            for l in range(output_nlinks):
                if latency_asic[l]==-1: 
                    latency_asic[l] = i
            # print(i,latency_asic)
            latency_asic,asic_found,daq_data = find_latency(latency_asic,'lc-ASIC')
            if -1 not in latency_asic.values():
                print('found!',latency_asic,asic_found)
                all_data['lc-ASIC'] = daq_data
                break

        # set fifo latency for lc-emulator
        # iterate over different fifo latencies
        latency_emulator = {}
        for l in range(output_nlinks):
            latency_emulator[l] = -1

        for i in range(0,511): # max fifo latency
            for l in range(output_nlinks):
                if latency_emulator[l]==-1:
                    latency_emulator[l] = i
            latency_emulator,emulator_found,daq_data = find_latency(latency_emulator,'lc-emulator',asic_found)
            if -1 not in latency_emulator.values():
                print('found!',latency_emulator)
                print('pos ',emulator_found,asic_found)
                all_data['lc-emulator'] = daq_data
                break

        for key,data in all_data.items():
            save_testvector("%s-alignoutput.csv"%key, data)

        # test stream-compare
        dev.getNode(names['stream_compare']+".control.reset").write(0x1) # start the counters from zero
        time.sleep(0.001)
        dev.getNode(names['stream_compare']+".control.latch").write(0x1)
        dev.dispatch()
        word_count = dev.getNode(names['stream_compare']+".word_count").read()
        err_count = dev.getNode(names['stream_compare']+".err_count").read()
        dev.dispatch()
        logger.info('Stream compare, word count %d, error count %d'%(word_count,err_count))
