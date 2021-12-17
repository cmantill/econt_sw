import uhal
import time
import argparse
import logging
logging.basicConfig()

from uhal_config import *
import utils_fc,utils_lc,utils_io,utils_tv

"""
Alignment sequence on tester using python2 uhal.

Usage:
   python testing/uhal-align_on_tester.py --step []
"""

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE, NONE",default='NONE')
    parser.add_argument('--step', 
                        choices=['init',
                                 'configure-IO',
                                 'check-IO',
                                 'test-data',
                                 'lr-roct',
                                 'lr-econt',
                                 'manual-lcASIC',
                                 'check-lcASIC',
                                 'capture',
                                 'latency',
                                 'compare',
                             ],
                        help='alignment steps')
    parser.add_argument('--invertIO', action='store_true', default=True, help='invert IO')

    parser.add_argument('--delay', type=int, default=None, help='delay data for emulator on tester')
    parser.add_argument('--bxlr', type=int, default=3540, help='When to send link reset roct')

    parser.add_argument('--alignpos', type=int, default=None, help='override align position by shifting it by this number')
    parser.add_argument('--lalign', type=str, default=None, help='links for which to override align position (default is all)')

    parser.add_argument('--lc', type=str, default='lc-ASIC', help='link capture to capture data with lrecont')
    parser.add_argument('--mode', type=str, default='L1A', help='options (BX,linkreset_ECONt,linkreset_ECONd,linkreset_ROCt,linkreset_ROCd,L1A,orbitSync)')
    parser.add_argument('--bx', type=int, default=0, help='bx')

    parser.add_argument('--dtype', type=str, default=None, help='dytpe (PRBS,debug)')
    parser.add_argument('--idir',dest="idir",type=str, default=None, help='test vector directory')

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
                utils_io.configure_IO(dev,io,io_name='IO',invert=True)
            else:
                utils_io.configure_IO(dev,io,io_name='IO')

    if args.step == "check-IO":
        """
        Check that IO block is aligned.
        Only "from" IO block needs this.
        """
        isIO_aligned = utils_io.check_IO(dev,io='from',nlinks=output_nlinks)
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
            logger.info("link %i: delay_out %i delay_out_N %i"%(link,delay_out,delay_out_N))

    if args.step == "init":
        """
        Initial configuration: The channel locks need bit transitions. 

        Configure link captures with align pattern.
        Set input clock.
        Send PRBS. (This should get us to PUSM_state 9.)
        """
        # fast command
        utils_fc.configure_fc(dev)

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
        utils_tv.set_testvectors(dev,"PRBS28")

    if args.step == "test-data":
        """
        Send test vectors data
          - dytpe = mode [PRBS,debug] for test vectors settings
          - 
        """
        utils_tv.set_testvectors(dev,args.dtype,args.idir)

    if args.step == "lr-roct":
        """
        Send link reset roc-t.
        Make e-link outputs send zeroes.
        Set delay for emulator.
        """
        # re-configure fc
        utils_fc.configure_fc(dev)
        dev.getNode(names['fc']+".bx_link_reset_roct").write(args.bxlr)
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
            utils_lc.configure_acquire(dev,lcapture,"linkreset_ECONt",nwords,output_nlinks)
            
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
        if args.lalign:
            links = [int(l) for l in args.lalign.split(',')]
        else:
            links = range(output_nlinks)
        for l in range(output_nlinks):
            align_pos = dev.getNode(names['lc-ASIC']['lc']+".link"+str(l)+".align_position").read();
            dev.dispatch()
            logger.info('Align pos link %i: %i'%(l,int(align_pos)))
            if args.alignpos and l in links:
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
        is_lcASIC_aligned = utils_lc.check_links(dev,'lc-ASIC',output_nlinks)

    if args.step == 'capture':
        # capture data
        nwords = 511 if 'input' in args.lc else 4095
        nlinks = input_nlinks if 'input' in args.lc else output_nlinks
        utils_lc.configure_acquire(dev,args.lc,args.mode,nwords,nlinks,args.bx)
        if args.mode == "linkreset_ECONt":
            utils_lc.do_fc_capture(dev,"link_reset_econt",args.lc)
            time.sleep(0.001)
            lrc = dev.getNode(names['fc-recv']+".counters.link_reset_econt").read();
            dev.dispatch()
            logger.info('link reset econt counter %i'%lrc)
        elif args.mode =="linkreset_ROCt":
            utils_lc.do_fc_capture(dev,"link_reset_roct",args.lc)
            time.sleep(0.001)
            lrc = dev.getNode(names['fc-recv']+".counters.link_reset_roct").read();
            dev.dispatch()
            logger.info('link reset roct counter %i'%lrc)
        else:
            utils_lc.do_capture(dev,args.lc)
        data = utils_lc.get_captured_data(dev,args.lc,nwords,nlinks)
        utils_tv.save_testvector("%s-alignoutput_debug.csv"%args.lc, data)

    if args.step == 'latency':
        """
        Capture data from ASIC link capture and find BX0 word
        """
        # re-configure fc
        utils_fc.configure_fc(dev)
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

        # find latency for ASIC
        for i in range(0,31):
            for l in range(output_nlinks):
                if latency['asic'][l]==-1: 
                    latency['asic'][l] = i

            latency['asic'],found_bx0['asic'],daq_data = utils_lc.find_latency(dev,latency['asic'],'lc-ASIC')
            if -1 not in latency['asic'].values():
                logger.info('Found BX0 for ASIC %s, %s',latency['asic'],found_bx0['asic'])
                all_data['lc-ASIC'] = daq_data
                break

        # find latency for emulator
        for i in range(0,31):
            for l in range(output_nlinks):
                if latency['emulator'][l]==-1:
                    latency['emulator'][l] = i
            latency['emulator'],found_bx0['emulator'],daq_data = utils_lc.find_latency(dev,latency['emulator'],'lc-emulator',found_bx0['asic'])
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
            utils_tv.save_testvector("%s-alignoutput.csv"%key, data)

    if args.step == 'compare':
        # setup fc
        dev.getNode(names['fc']+".command.global_l1a_enable").write(1);
        dev.dispatch();

        # setup link captures just in case
        for lcapture in ['lc-ASIC','lc-emulator']:
            nwords = 511 if 'input' in args.lc else 4095
            nlinks = input_nlinks if 'input' in lcapture else output_nlinks
            utils_lc.configure_acquire(dev,lcapture,"L1A",nwords,nlinks=nlinks)
            utils_lc.do_capture(dev,lcapture)

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
            # dev.getNode(names['stream_compare']+".trigger").write(0x1)
            # dev.dispatch()
            # dev.getNode(names['stream_compare']+".trigger").write(0x0)
            # dev.dispatch()
            
            # send manual L1A
            utils_fc.send_l1a(dev)

            # get data
            all_data = {}
            for lcapture in ['lc-ASIC','lc-emulator']:
                nlinks = input_nlinks if 'input' in lcapture else output_nlinks
                nwords = 511 if 'input' in args.lc else 4095
                all_data[lcapture] = utils_lc.get_captured_data(dev,lcapture,nwords=nwords,nlinks=nlinks)

            for key,data in all_data.items():
                utils_tv.save_testvector( "align-%s-sc.csv"%key, data, header=True)
        
        # reset fc
        dev.getNode(names['fc']+".command.global_l1a_enable").write(0);
        dev.dispatch();
