import uhal
import time
import argparse
import logging
logging.basicConfig()

from utils.uhal_config  import *
import utils.fast_command as utils_fc
import utils.link_capture as utils_lc
import utils.io as utils_io
import utils.test_vectors as utils_tv

from capture import reset_lc

def configure_io(dev,args):
    for io in args.io_names.split(','):
        if args.invertIO:
            utils_io.configure_IO(dev,io,io_name='IO',invert=True)
        else:
            utils_io.configure_IO(dev,io,io_name='IO')

def init(dev,args):
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

    # configure lc with default sync words
    for lcapture in ['lc-input','lc-ASIC','lc-emulator']:
        reset_lc(dev,lcapture)
        
    # set input clock (40MHz)
    dev.getNode("housekeeping-AXI-mux-0.select").write(0);
    dev.dispatch()
    
    # send 28 bit PRBS
    utils_tv.set_testvectors(dev,"PRBS28")

def lr_roct(dev,args):
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

def lr_econt(dev,args):
    # reset lc
    for lcapture in ['lc-input','lc-ASIC','lc-emulator']:
        reset_lc(dev,lcapture)

    # configure acquire
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

def manual_align(dev,args,lcapture='lc-ASIC'):
    if args.lalign:
        links = [int(l) for l in args.lalign.split(',')]
    else:
        links = range(output_nlinks)

    # set link_align_inhibit so that link capture ignores link reset (for all elinks)
    disable_alignment(dev,lcapture)

    for l in links:
        align_pos = dev.getNode(names[lcapture]['lc']+".link"+str(l)+".align_position").read();
        dev.dispatch()
        
        logger.info('Align pos link %i: %i'%(l,int(align_pos)))
        if args.alignpos and l in links:
            dev.getNode(names[lcapture]['lc']+".link"+str(l)+".override_align_position").write(1);
            dev.getNode(names[lcapture]['lc']+".link"+str(l)+".align_position").write(int(align_pos)+args.alignpos);
            dev.dispatch()

            read_align_pos = dev.getNode(names[lcapture]['lc']+".link"+str(l)+".align_position").read();
            dev.dispatch()
            logger.info('Set align pos link %i: %i'%(l,read_align_pos))

            dev.getNode(names[lcapture]['lc']+".link"+str(l)+".explicit_align").write(1);
            dev.dispatch()

def modify_latency(dev,args):
    # re-configure fc
    utils_fc.configure_fc(dev)
    dev.getNode(names['fc']+".bx_link_reset_econt").write(3502)
    dev.dispatch()
    
    all_data = dict.fromkeys(['lc-ASIC','lc-emulator'])
    latency={
        'lc-ASIC': dict.fromkeys(range(output_nlinks), -1),
        'lc-emulator': dict.fromkeys(range(output_nlinks), -1),
    }
    found_bx0 = {
        'lc-ASIC': dict.fromkeys(range(output_nlinks), -1),
        'emulator': dict.fromkeys(range(output_nlinks), -1),
    }
    
    def find_bx0(lc,lat,fbx0,all_data,ref=None):
        for i in range(0,31):
            for l in range(output_nlinks):
                if latency[lc][l]==-1:
                    latency[lc][l] = i
            lat[lc],fbx0[lc],daq_data = utils_lc.find_latency(dev,lat[lc],lc,ref)
            if -1 not in lat[lc].values():
                logger.info('Found BX0 for %s: %s, %s',lc,lat[lc],fbx0[lc])
                all_data[lc] = daq_data
                if ref:
                    if fbx0[lc][0] > ref[0]:
                        logger.info('Repeat ASIC')
                        return True
                break
        return False

    # find latency for ASIC
    find_bx0('lc-ASIC',latency,found_bx0,all_data)
    
    # find latency for emulator
    repeat_ASIC  = find_bx0('lc-emulator',latency,found_bx0,all_data,found_bx0['lc-ASIC'])
    if repeat_ASIC:
        print(found_bx0['lc-emulator'],latency['lc-emulator'])
        find_bx0('lc-ASIC',latency,found_bx0,all_data,found_bx0['lc-emulator'])

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

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE",default='INFO')
    parser.add_argument('--step', 
                        choices=['init',
                                 'configure-IO',
                                 'manual-IO',
                                 'lr-roct',
                                 'lr-econt',
                                 'manual-lcASIC',
                                 'latency',
                             ],
                        help='alignment steps')
    parser.add_argument('--io_names', type=str, default='to,from', help='IO block names to configure')
    parser.add_argument('--invertIO', action='store_true', default=False, help='invert IO')
    parser.add_argument('--delay', type=int, default=None, help='delay data for emulator on tester')
    parser.add_argument('--bxlr', type=int, default=3540, help='When to send link reset roct')
    args = parser.parse_args()

    set_logLevel(args)
    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")

    logger = logging.getLogger('align:step:%s'%args.step)
    try:
        logger.setLevel(args.logLevel)
    except ValueError:
        logging.error("Invalid log level")
        exit(1)

    if args.step == "configure-IO":
        configure_io(dev,args)

    if args.step == "manual-IO":
        utils_io.manual_IO(dev,"from","IO")

    if args.step == "init":
        init(dev,args)

    if args.step == "lr-roct":
        lr_roct(dev,args)
        
    if args.step == "lr-econt":
        lr_econt(dev,args)

    if args.step == 'manual-lcASIC':
        manual_align(dev,args,lcapture='lc-ASIC')

    if args.step == 'latency':
        modify_latency(dev,args)
