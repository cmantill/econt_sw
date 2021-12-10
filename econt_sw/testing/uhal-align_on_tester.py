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
   python testing/uhal-align_on_tester.py --step []
"""

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE, NONE",default='NONE')
    parser.add_argument('--step', choices=['configure-IO',
                                           'check-IO',
                                           'prbs-data',
                                           'zero-data',
                                           'lr-roct',
                                           'lr-econt',
                                           'manual-lcASIC',
                                           'check-lcASIC',
                                           'capture',
                                           'latency',
                                           'compare',
                                           ],
                        help='alignment steps')
    parser.add_argument('--invertIO', action='store_true', default=False, help='invert IO')
    parser.add_argument('--delay', type=int, default=None, help='delay data for emulator on tester')
    parser.add_argument('--alignpos', type=int, default=None, help='override align position by shifting it by this number')
    parser.add_argument('--lc', type=str, default='lc-ASIC', help='link capture to capture data with lrecont')
    parser.add_argument('--mode', type=str, default=None, help='options (BX,linkreset_ECONt,linkreset_ECONd,linkreset_ROCt,linkreset_ROCd,L1A,orbitSync)')
    parser.add_argument('--bx', type=int, default=0, help='bx')

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

    if args.step == "configure-IO":
        for io in names['IO'].keys():
            if args.invertIO:
                configure_IO(dev,io,io_name='IO',invert=True)
            else:
                configure_IO(dev,io,io_name='IO')

    if args.step == "check-IO":
        """
        Check that IO block is aligned.
        Only "from" IO block needs this.
        """
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

    if args.step == "prbs-data":
        """
        Initial configuration: The channel locks need bit transitions. 

        Configure link captures with align pattern.
        Set input clock.
        Send PRBS. (This should get us to PUSM_state 9.)
        """
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
            #"header_mask": 0x00000000,
            "header": 0xa0000000,
            "header_BX0": 0x90000000,
        }
        print(testvectors_settings)
        for l in range(input_nlinks):
            for key,value in testvectors_settings.items():
                dev.getNode(names['testvectors']['switch']+".link"+str(l)+"."+key).write(value)
            dev.getNode(names['testvectors']['stream']+".link"+str(l)+".sync_mode").write(0x1)
            dev.getNode(names['testvectors']['stream']+".link"+str(l)+".ram_range").write(0x1)
            dev.getNode(names['testvectors']['stream']+".link"+str(l)+".force_sync").write(0x0)
        dev.dispatch()

    if args.step == "zero-data":
        # setup normal output
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

        # configure bypass (for emulator)
        for l in range(output_nlinks):
            dev.getNode(names['bypass']['switch']+".link"+str(l)+".output_select").write(0x1)
        dev.dispatch()

        # set delay (for emulator)
        if args.delay:
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
                    dev.getNode(names[lcapture]['lc']+".link"+str(l)+".link_align_inhibit").write(0);
                    dev.getNode(names[lcapture]['lc']+".link"+str(l)+".override_align_position").write(0);
                    dev.dispatch()
        
        for lcapture in ['lc-ASIC','lc-emulator']:
            # configure link captures to acquire on linkreset-ECONt (4095 words)
            nwords = 4095
            configure_acquire(dev,lcapture,"linkreset_ECONt",nwords,output_nlinks)
            
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
            if args.alignpos:
                # set override
                dev.getNode(names['lc-ASIC']['lc']+".link"+str(l)+".override_align_position").write(1);
                # set align position (manually to +/-16 in this case)
                dev.getNode(names['lc-ASIC']['lc']+".link"+str(l)+".align_position").write(int(align_pos)+args.alignpos);
                dev.dispatch()
                read_align_pos = dev.getNode(names['lc-ASIC']['lc']+".link"+str(l)+".align_position").read();
                dev.dispatch()
                logger.info('Set align pos link %i: %i'%(l,read_align_pos))
                # force to autoalign
                dev.getNode(names['lc-ASIC']['lc']+".link"+str(l)+".explicit_align").write(1);
                # set link_align_inhibit so that link capture ignores link reset
                dev.getNode(names['lc-ASIC']['lc']+".link"+str(l)+".link_align_inhibit").write(1);
                dev.dispatch()

    if args.step == 'check-lcASIC':
        """
        Check that link capture ASIC is aligned.
        If not, capture data.
        """
        # check that links are aligned
        is_lcASIC_aligned = check_links(dev,'lc-ASIC',output_nlinks)

    if args.step == 'capture':
        # capture data
        nwords = 511 if 'input' in args.lc else 4095
        nlinks = input_nlinks if 'input' in args.lc else output_nlinks
        configure_acquire(dev,args.lc,args.mode,nwords,nlinks,args.bx)
        if args.mode == "linkreset_ECONt":
            do_fc_capture(dev,"link_reset_econt",args.lc)
            time.sleep(0.001)
            lrc = dev.getNode(names['fc-recv']+".counters.link_reset_econt").read();
            dev.dispatch()
            logger.info('link reset econt counter %i'%lrc)
        elif args.mode =="linkreset_ROCt":
            do_fc_capture(dev,"link_reset_roct",args.lc)
            time.sleep(0.001)
            lrc = dev.getNode(names['fc-recv']+".counters.link_reset_roct").read();
            dev.dispatch()
            logger.info('link reset roct counter %i'%lrc)
        else:
            do_capture(dev,args.lc)
        data = get_captured_data(dev,args.lc,nwords,nlinks)
        save_testvector("%s-alignoutput_debug.csv"%args.lc, data)

    if args.step == 'latency':
        """
        Capture data from ASIC link capture and find BX0 word
        """
        # re-configure fc
        configure_fc(dev)
        dev.getNode(names['fc']+".bx_link_reset_econt").write(3502)
        dev.dispatch()
        
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

            latency['asic'],found_bx0['asic'],daq_data = find_latency(dev,latency['asic'],'lc-ASIC')
            if -1 not in latency['asic'].values():
                logger.info('Found BX0 for ASIC %s, %s',latency['asic'],found_bx0['asic'])
                all_data['lc-ASIC'] = daq_data
                break

        # loop over possible values of fifo latency
        for i in range(0,31):
            for l in range(output_nlinks):
                if latency['emulator'][l]==-1:
                    latency['emulator'][l] = i
            latency['emulator'],found_bx0['emulator'],daq_data = find_latency(dev,latency['emulator'],'lc-emulator',found_bx0['asic'])
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

    if args.step == 'compare':
        # setup fc
        dev.getNode(names['fc']+".command.global_l1a_enable").write(1);
        dev.dispatch();

        # setup link captures just in case
        acq_length = 511
        for lcapture in ['lc-ASIC','lc-emulator']:
            nlinks = input_nlinks if 'input' in lcapture else output_nlinks
            configure_acquire(dev,lcapture,"L1A",nwords=acq_length,nlinks=nlinks)
            do_capture(dev,lcapture)

        # make sure that stream-compare sees no errors
        dev.getNode(names['stream_compare']+".control.reset").write(0x1) # start the counters from zero
        time.sleep(0.001)
        dev.getNode(names['stream_compare']+".control.latch").write(0x1) # latch the counters
        dev.dispatch()
        word_count = dev.getNode(names['stream_compare']+".word_count").read()
        err_count = dev.getNode(names['stream_compare']+".err_count").read()
        dev.dispatch()
        logger.info('Stream compare, word count %d, error count %d'%(word_count,err_count))

        if err_count > 0:
            dev.getNode(names['stream_compare']+".trigger").write(0x1)
            dev.dispatch()
                
            all_data = {}
            for lcapture in ['lc-ASIC','lc-emulator']:
                nlinks = input_nlinks if 'input' in lcapture else output_nlinks
                all_data[lcapture] = get_captured_data(dev,lcapture,nwords=acq_length,nlinks=nlinks)

            for key,data in all_data.items():
                save_testvector( "align-%s-sc.csv"%key, data, header=True)
        
        # reset fc
        dev.getNode(names['fc']+".command.global_l1a_enable").write(0);
        dev.dispatch();
