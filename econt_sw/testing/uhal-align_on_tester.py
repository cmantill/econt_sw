import uhal
import time
import argparse
import logging
logging.basicConfig()

from uhal_config import names,input_nlinks,output_nlinks
from uhal_utils import check_IO,check_links,configure_IO,get_captured_data,save_testvector,configure_acquire,do_fc_capture

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
    # record the position at which BX0 was found for each elink (this needs to be the same for all elinks)
    found_BX0 = {}

    # set latency
    for l in range(output_nlinks):
        dev.getNode(names[lcapture]['lc']+".link"+str(l)+".fifo_latency").write(latency[l]);
    dev.dispatch()

    # read latency
    read_latency = {}
    for l in range(output_nlinks):
        lat = dev.getNode(names[lcapture]['lc']+".link"+str(l)+".fifo_latency").read();
        dev.dispatch()
        read_latency[l] = int(lat)
    logger.debug('Written latencies: %s',latency)
    logger.debug('Read latencies: %s',read_latency)

    # do one capture on link reset econt
    do_fc_capture(dev,"link_reset_econt",lcapture)
    
    # check link reset econt counter
    lrc = dev.getNode(names['fc-recv']+".counters.link_reset_econt").read()
    dev.dispatch()
    logger.info('link reset econt counter %i'%lrc) 

    # save captured data
    use_numpy =False
    ASIC_data = get_captured_data(dev,lcapture,nwords=4095,nlinks=output_nlinks)
    # save_testvector("lc-ASIC-findlatency-debug.csv", ASIC_data)

    # look for bx0
    BX0_word = 0xf922f922
    if use_numpy:
        BX0_rows,BX0_cols = (ASIC_data == BX0_word).nonzero()
        logger.debug('BX0 sync word found on columns %s',BX0_cols)
        logger.debug('BX0 sync word found on rows %s',BX0_rows)
        try: 
            assert len(BX0_rows) > 0
            assert (BX0_cols==0).nonzero()
        except AssertionError:
            logger.error('BX0 sync word not found anywhere or in link 0')
            for l in range(output_nlinks):
                new_latency[l] = -1
            return new_latency,found_BX0,ASIC_data
    else:
        BX0_rows = []
        BX0_cols = []
        for i,d in enumerate(ASIC_data):
            if BX0_word in d:
                BX0_rows.append(i)
                for j,col in enumerate(d):
                    if BX0_word==col and j not in BX0_cols:
                        BX0_cols.append(j)
            
        logger.debug('BX0 sync word found on columns %s',BX0_cols)
        logger.debug('BX0 sync word found on rows %s',BX0_rows)
        try:
            assert len(BX0_rows) > 0
            assert 0 in BX0_cols 
            logger.debug('Found BX0 in link 0 ')
        except AssertionError:
            logger.error('BX0 sync word not found anywhere or in link 0')
            for l in range(output_nlinks):
                new_latency[l] = -1
                return new_latency,found_BX0,ASIC_data
        logger.debug('BX0 sync word found on columns %s',BX0_cols)
        logger.debug('BX0 sync word found on rows %s',BX0_rows)

    for l in range(output_nlinks):
        if use_numpy:
            try:
                row_index = (BX0_cols==l).nonzero()[0][0]
                row_link_0 = (BX0_cols==0).nonzero()[0][0]
                assert BX0_rows[row_index] == BX0_rows[row_link_0]
                if bx0:
                    assert BX0_rows[row_index] == bx0[row_index]
                logger.debug('Latency %i: %s found BX0 word at %d',latency[l],lcapture,BX0_rows[row_index])
                new_latency[l] = latency[l]
                found_BX0[l] = BX0_rows[row_index]
            except AssertionError:
                if bx0:
                    logger.warning('BX0 sync word not found for link %i at (pos of link 0): %i or (pos of where bx0 was found for ASIC): %i'%(l,BX0_rows[row_link_0],bx0[row_index]))
                else:
                    logger.warning('BX0 sync word not found for link %i at (pos of link 0): %i'%(l,BX0_rows[row_link_0]))
                new_latency[l] = -1
        else:
            try:
                print(BX0_rows.count(BX0_rows[0]))
                print(BX0_rows.count(bx0[0]))

                assert BX0_rows.count(BX0_rows[0]) == len(BX0_rows)
                if bx0:
                    assert BX0_rows.count(bx0[0]) == len(BX0_rows)
                logger.debug('Latency %i: %s found BX0 word at %d',latency[l],lcapture,BX0_rows[l])
                new_latency[l] = latency[l]
                #found_BX0[l] = BX0_rows[row_index
            except AssertionError:
                if bx0:
                    logger.warning('BX0 sync word not found for link %i at (pos of link 0): %i or (pos of where bx0 was found for ASIC): %i'%(l,BX0_rows[row_link_0],bx0[row_index]))
                else:
                    logger.warning('BX0 sync word not found for link %i at (pos of link 0): %i'%(l,BX0_rows[row_link_0]))
                new_latency[l] = -1
    return new_latency,found_BX0,ASIC_data
        
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE, NONE",default='NONE')
    parser.add_argument('--step', choices=['test','tester-phase','asic-word','asic-tester'], help='alignment steps')
    
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
    logger.setLevel(logging.DEBUG)

    if args.step == "test":
        # configure IO blocks
        for io in names['IO'].keys():
            configure_IO(dev,io,io_name='IO')
            nlinks = input_nlinks if io=='to' else output_nlinks
            for l in range(nlinks):
                dev.getNode(names['IO'][io]+".link"+str(l)+".reg0.invert").write(0x1)
            dev.dispatch()

        # fast command
        dev.getNode(names['fc']+".command.enable_fast_ctrl_stream").write(0x1);
        dev.getNode(names['fc']+".command.enable_orbit_sync").write(0x1);
        dev.getNode(names['fc']+".command.global_l1a_enable").write(0);
        dev.getNode(names['fc']+".bx_link_reset_roct").write(3500)
        dev.getNode(names['fc']+".bx_link_reset_rocd").write(3501)
        dev.getNode(names['fc']+".bx_link_reset_econt").write(3502)
        dev.getNode(names['fc']+".bx_link_reset_econd").write(3503)

        # configure link captures
        sync_patterns = {'lc-ASIC': 0x122,
                         'lc-emulator': 0x122,
                         'lc-input': 0xaccccccc,
                     }
        for lcapture in ['lc-input','lc-ASIC','lc-emulator']:
            dev.getNode(names[lcapture]['lc']+".global.link_enable").write(0x1fff)
            dev.getNode(names[lcapture]['lc']+".global.explicit_resetb").write(0x0)
            time.sleep(0.001)
            dev.getNode(names[lcapture]['lc']+".global.explicit_resetb").write(0x1)
            dev.dispatch()
            nlinks = input_nlinks if 'input' in lcapture else output_nlinks
            for l in range(nlinks):
                dev.getNode(names[lcapture]['lc']+".link"+str(l)+".align_pattern").write(sync_patterns[lcapture])
                dev.getNode(names[lcapture]['lc']+".link"+str(l)+".fifo_latency").write(0);
                dev.dispatch()

        for lcapture in ['lc-ASIC','lc-emulator']:
            # configure link captures to acquire on linkreset-ECONt (4095 words)
            configure_acquire(dev,lcapture,"linkreset_ECONt",nwords=4095,nlinks=output_nlinks)

        # send link reset econt (once)
        lrc = dev.getNode(names['fc-recv']+".counters.link_reset_econt").read();
        dev.dispatch()
        logger.info('link reset econt counter %i'%lrc)

        dev.getNode(names['fc']+".bx_link_reset_econt").write(3550)
        dev.dispatch()
        dev.getNode(names['fc']+".request.link_reset_econt").write(0x1);
        dev.dispatch()
        time.sleep(0.1)

        lrc = dev.getNode(names['fc-recv']+".counters.link_reset_econt").read();
        dev.dispatch()
        logger.info('link reset econt counter %i'%lrc)

        # capture data                                                                                                                                                                                  
        raw_input("Need to capture data in output. Press key to continue...")
        do_fc_capture(dev,"link_reset_econt",'lc-ASIC')
        time.sleep(0.001)
        lrc = dev.getNode(names['fc-recv']+".counters.link_reset_econt").read();
        dev.dispatch()
        logger.info('link reset econt counter %i'%lrc)
        data = get_captured_data(dev,'lc-ASIC',nwords=4095,nlinks=output_nlinks)
        save_testvector("lc-ASIC-alignoutput_debug.csv", data)
        raw_input("Sent link reset ECONT. Press key to continue...")
        exit(1)
    
    if args.step == "tester-phase":
        # configure IO blocks
        for io in names['IO'].keys():
            configure_IO(dev,io,io_name='IO')
            nlinks = input_nlinks if io=='to' else output_nlinks
            for l in range(nlinks):
                dev.getNode(names['IO'][io]+".link"+str(l)+".reg0.invert").write(0x1)        
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

        # configure fast command
        dev.getNode(names['fc']+".command.enable_fast_ctrl_stream").write(0x1);
        dev.getNode(names['fc']+".command.enable_orbit_sync").write(0x1);
        dev.getNode(names['fc']+".command.global_l1a_enable").write(0);

        # configure BXs
        dev.getNode(names['fc']+".bx_link_reset_roct").write(3500)
        dev.getNode(names['fc']+".bx_link_reset_rocd").write(3501)
        dev.getNode(names['fc']+".bx_link_reset_econt").write(3502)
        dev.getNode(names['fc']+".bx_link_reset_econd").write(3503)
        
        # send link reset ECONT
        lrc = dev.getNode(names['fc-recv']+".counters.link_reset_roct").read();
        dev.dispatch()
        logger.info('link reset roct counter %i'%lrc)

        dev.getNode(names['fc']+".request.link_reset_roct").write(0x1);
        dev.dispatch()
        time.sleep(2)

        lrc = dev.getNode(names['fc-recv']+".counters.link_reset_roct").read();
        dev.dispatch()
        logger.info('link reset roct counter %i'%lrc)

        raw_input("Sent link reset ROCT. Press key to continue...")

        # check that from-IO is aligned
        isIO_aligned = check_IO(dev,io='from',nlinks=output_nlinks)
        if isIO_aligned:
            logger.info("from-IO aligned")
        else:
            logger.info("from-IO is not aligned")
            exit(1)

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

        # configure fast command
        dev.getNode(names['fc']+".command.enable_fast_ctrl_stream").write(0x1);
        dev.getNode(names['fc']+".command.enable_orbit_sync").write(0x1);
        dev.getNode(names['fc']+".command.global_l1a_enable").write(0);

        # set BXs
        dev.getNode(names['fc']+".bx_link_reset_roct").write(3500)
        dev.getNode(names['fc']+".bx_link_reset_rocd").write(3501)
        dev.getNode(names['fc']+".bx_link_reset_econt").write(3502)
        dev.getNode(names['fc']+".bx_link_reset_econd").write(3503)
        
        # set delay
        delay = 4
        dev.getNode(names['delay']+".delay").write(delay)

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
        sync_patterns = {'lc-ASIC': 0x122,
                         'lc-emulator': 0x122,
                         'lc-input': 0xaccccccc,
                     }
        for lcapture in ['lc-input','lc-ASIC','lc-emulator']:
            dev.getNode(names[lcapture]['lc']+".global.link_enable").write(0x1fff)
            dev.getNode(names[lcapture]['lc']+".global.explicit_resetb").write(0x0)
            time.sleep(0.001)
            dev.getNode(names[lcapture]['lc']+".global.explicit_resetb").write(0x1)
            dev.dispatch()
            # set align pattern
            nlinks = input_nlinks if 'input' in lcapture else output_nlinks
            for l in range(nlinks):
                dev.getNode(names[lcapture]['lc']+".link"+str(l)+".align_pattern").write(sync_patterns[lcapture])
                dev.getNode(names[lcapture]['lc']+".link"+str(l)+".fifo_latency").write(0);
                dev.dispatch()
        
        for lcapture in ['lc-ASIC','lc-emulator']:
            # configure link captures to acquire on linkreset-ECONt (4095 words)
            configure_acquire(dev,lcapture,"linkreset_ECONt",nwords=4095,nlinks=output_nlinks)
            
        # send link reset econt (once)
        lrc = dev.getNode(names['fc-recv']+".counters.link_reset_econt").read();
        dev.dispatch()
        logger.info('link reset econt counter %i'%lrc)

        dev.getNode(names['fc']+".bx_link_reset_econt").write(3550)
        dev.dispatch()
        dev.getNode(names['fc']+".request.link_reset_econt").write(0x1);
        dev.dispatch()
        time.sleep(0.1)

        lrc = dev.getNode(names['fc-recv']+".counters.link_reset_econt").read();
        dev.dispatch()
        logger.info('link reset econt counter %i'%lrc)

        # check that links are aligned
        is_lcASIC_aligned = check_links(dev,lcapture='lc-ASIC',nlinks=output_nlinks)
        if not is_lcASIC_aligned:
            # capture data
            raw_input("Need to capture data in output. Press key to continue...")
            do_fc_capture(dev,"link_reset_econt",'lc-ASIC')
            time.sleep(0.001)
            lrc = dev.getNode(names['fc-recv']+".counters.link_reset_econt").read();
            dev.dispatch()
            logger.info('link reset econt counter %i'%lrc)
            data = get_captured_data(dev,'lc-ASIC',nwords=4095,nlinks=output_nlinks)
            save_testvector("lc-ASIC-alignoutput_debug.csv", data)
            raw_input("Sent link reset ECONT. Press key to continue...")
            exit(1)

        # data to be captured
        all_data = {}
                
        # set fifo latency (initiate with default values of -1)
        latency={'asic': dict.fromkeys(range(output_nlinks), -1),
                 'emulator': dict.fromkeys(range(output_nlinks), -1),
             }
        found_bx0 = {'asic': dict.fromkeys(range(output_nlinks), -1),
                     'emulator': dict.fromkeys(range(output_nlinks), -1),
                 }

        # loop over possible values of fifo latency
        for i in range(0,31):
            for l in range(output_nlinks):
                if latency['asic'][l]==-1: 
                    latency['asic'][l] = i

            latency['asic'],found_bx0['asic'],daq_data = find_latency(latency['asic'],'lc-ASIC')
            if -1 not in latency['asic'].values():
                logger.info('Found BX0 for ASIC %s, %s',latency['asic'],found_bx0['asic'])
                all_data['lc-ASIC'] = daq_data
                break

        # loop over possible values of fifo latency
        for i in range(0,31):
            for l in range(output_nlinks):
                if latency['emulator'][l]==-1:
                    latency['emulator'][l] = i
            latency['emulator'],found_bx0['emulator'],daq_data = find_latency(latency['emulator'],'lc-emulator',found_bx0['asic'])
            if -1 not in latency['emulator'].values():
                logger.info('Found BX0 for emulator %s, %s',latency['emulator'],found_bx0['emulator'])
                all_data['lc-emulator'] = daq_data
                break

        # read values of latency (to cross check)
        latency_values = {}
        for lcapture in ['lc-ASIC','lc-emulator']:
            latency_values[lcapture] = []
            for l in range(output_nlinks):
                latency = dev.getNode(names[lcapture]['lc']+".link"+str(l)+".fifo_latency").read();
                dev.dispatch()
                latency_values[lcapture].append(int(latency))
        logger.debug('Final latency values: %s',latency_values)

        # save captured data
        for key,data in all_data.items():
            save_testvector("%s-alignoutput.csv"%key, data)

        # make sure that stream-compare sees no errors
        dev.getNode(names['stream_compare']+".control.reset").write(0x1) # start the counters from zero
        time.sleep(0.001)
        dev.getNode(names['stream_compare']+".control.latch").write(0x1)
        dev.dispatch()
        word_count = dev.getNode(names['stream_compare']+".word_count").read()
        err_count = dev.getNode(names['stream_compare']+".err_count").read()
        dev.dispatch()
        logger.info('Stream compare, word count %d, error count %d'%(word_count,err_count))
