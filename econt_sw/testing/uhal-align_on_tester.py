import uhal
import time
import argparse
import logging
logging.basicConfig()

from uhal_config import *
from uhal_utils import *

"""
Alignment sequence on tester using python2 uhal.

Usage:
   python testing/uhal-align_on_tester.py --step [bit-tr,check-IO,lr-roct,lr-econt,manual-lcASIC,check-lcASIC,capture]
"""
        
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE, NONE",default='NONE')
    parser.add_argument('--step', choices=['bit-tr',
                                           'check-IO',
                                           'lr-roct',
                                           'lr-econt',
                                           'manual-lcASIC',
                                           'check-lcASIC',
                                           'capture',
                                           ],
                        help='alignment steps')
    parser.add_argument('--invertIO', action='store_true', default=False, help='invert IO')
    parser.add_argument('--delay', type=int, default=4, help='delay data for emulator on tester')
    parser.add_argument('--alignpos', type=int, default=0, help='override align position by shifting it by this number')
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

    if args.step == "bit-tr":
        """
        Initial configuration: The channel locks need bit transitions. And the IO blocks do too.

        Configure IO/fc.
        Configure link captures with align pattern.
        Set input clock.
        Send PRBS. (This should get us to PUSM_state 9.)
        """

        # configure IO blocks
        for io in names['IO'].keys():
            if args.invertIO:
                configure_IO(dev,io,io_name='IO',invert=True)
            else:
                configure_IO(dev,io,io_name='IO')

        # fast command
        configure_fc(dev)

        # configure BXs to send link resets
        dev.getNode(names['fc']+".bx_link_reset_roct").write(3500)
        dev.getNode(names['fc']+".bx_link_reset_rocd").write(3501)
        dev.getNode(names['fc']+".bx_link_reset_econt").write(3502)
        dev.getNode(names['fc']+".bx_link_reset_econd").write(3503)
        dev.dispatch()

        # configure link captures
        sync_patterns = {
            'lc-ASIC': 0x122,
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
                if lcapture=="lc-ASIC":
                    # reverse bit for lc
                    dev.getNode(names[lcapture]['lc']+".link"+str(l)+".delay.bit_reverse").write(1);
                    dev.dispatch()

        # set input clock (40MHz)
        dev.getNode("housekeeping-AXI-mux-0.select").write(0);
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

    if args.step == "check-IO":
        """
        Check that IO block is aligned.
        Only "from" IO block needs this.
        """
        # check that from-IO is aligned
        isIO_aligned = check_IO(dev,io='from',nlinks=output_nlinks)
        if isIO_aligned:
            logger.info("from-IO aligned")
        else:
            logger.info("from-IO is not aligned")
            exit(1)

        # check eye width
        for link in range(output_nlinks):
            delay_out = dev.getNode(names['IO']['from']+".link%i"%link+".reg3.delay_out").read()
            delay_out_N = dev.getNode(names['IO']['from']+".link%i"%link+".reg3.delay_out_N").read()
            dev.dispatch()

    if args.step == "lr-roct":
        """
        Send link reset roc-t.
        Make e-link outputs send zeroes.
        Set delay for emulator.
        """
        # re-configure fc
        configure_fc(dev)
        dev.getNode(names['fc']+".bx_link_reset_roct").write(3500)
        dev.dispatch()

        # setup normal output in test-vectors
        out_brams = []
        testvectors_settings = {
            "output_select": 0x0,
            "n_idle_words": 255,
            "idle_word": 0xaccccccc,
            "idle_word_BX0": 0x9ccccccc,
            #"idle_word": 0xa0000000, # useful for debug
            #"idle_word_BX0": 0x90000000,
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

        # configure bypass (for emulator)
        for l in range(output_nlinks):
            dev.getNode(names['bypass']['switch']+".link"+str(l)+".output_select").write(0x1)
        dev.dispatch()

        # set delay (for emulator)
        # is this the right place to set it?
        dev.getNode(names['delay']+".delay").write(args.delay)
        dev.dispatch()

        # send a link reset roct
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
        
        """
        if args.saveinput:
            # configure lc input
            sync_patterns = {
                'lc-input': 0xaccccccc,
            }
            for lcapture in ['lc-input']:
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
                nwords = 4095
                configure_acquire(dev,lcapture,"linkreset_ROCt",nwords=nwords,nlinks=nlinks)

            # send another
            do_fc_capture(dev,"link_reset_econt",'lc-input')
            nwords = 4095
            data = get_captured_data(dev,'lc-input',nwords=nwords,nlinks=input_nlinks)
            save_testvector("lc-input-alignoutput_debug.csv", data)
        """

    if args.step == "lr-econt":
        """
        Send link reset econ-t.
        Re-configure link captures.
        """
        
        # re-configure link captures
        sync_patterns = {
            'lc-ASIC': 0x122,
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
                if lcapture=="lc-ASIC":
                    # reverse bit for lc
                    dev.getNode(names[lcapture]['lc']+".link"+str(l)+".delay.bit_reverse").write(1);
                    dev.dispatch()
        
        for lcapture in ['lc-ASIC','lc-emulator']:
            # configure link captures to acquire on linkreset-ECONt (4095 words)
            nwords = 4095
            configure_acquire(dev,lcapture,"linkreset_ECONt",nwords=nwords,nlinks=output_nlinks)
            
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

    if args.step == 'manual-lcASIC':
        """ 
        Manually override link capture ASIC
        """
        for l in range(output_nlinks):
            align_pos = dev.getNode(names['lc-ASIC']['lc']+".link"+str(l)+".align_position").read();
            dev.dispatch()
            logger.info('Align pos link %i: %i'%(l,int(align_pos)))
            # set override
            dev.getNode(names['lc-ASIC']['lc']+".link"+str(l)+".override_align_position").write(1);
            dev.dispatch()
            # set align position (manually to +/-16 in this case)
            dev.getNode(names['lc-ASIC']['lc']+".link"+str(l)+".align_position").write(int(align_pos)+args.alignpos);
            dev.dispatch()
            # force to autoalign
            dev.getNode(names['lc-ASIC']['lc']+".link"+str(l)+".explicit_align").write(1);
            dev.dispatch()

    if args.step == 'check-lcASIC':
        """
        Check that link capture ASIC is aligned.
        If not, capture data.
        """
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
            nwords = 4095
            data = get_captured_data(dev,'lc-ASIC',nwords=nwords,nlinks=output_nlinks)
            save_testvector("lc-ASIC-alignoutput_debug.csv", data)
            raw_input("Sent link reset ECONT. Press key to continue...")
            exit(1)

    if args.step == 'capture':
        """
        Capture data from ASIC link capture and find BX0 word
        """
        
        # data to be captured
        all_data = {}
                
        # set fifo latency (initiate with default values of -1)
        latency={
            'asic': dict.fromkeys(range(output_nlinks), -1),
            'emulator': dict.fromkeys(range(output_nlinks), -1),
        }
        found_bx0 = {
            'asic': dict.fromkeys(range(output_nlinks), -1),
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
