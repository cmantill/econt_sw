import uhal
import time
import argparse

import logging
logging.basicConfig()

from utils.uhal_config  import *
from utils.io import IOBlock
from utils.fast_command import FastCommands
from utils.link_capture import LinkCapture
from utils.test_vectors import TestVectors
from utils.stream_compare import StreamCompare

from_io = IOBlock('from')
to_io = IOBlock('to')
fc = FastCommands()
lc = LinkCapture()
tv = TestVectors()
sc = StreamCompare()


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

 def find_latency(latency,lcapture,bx0=None,savecap=False):
     """
     Find with that latency we see the BX0 word.
     It captures on link reset econt so capture block needs to set acquire to that.
     If `bx0[l]` is set, then check that that position at which BX0 word is found, is the same as bx0.
     """

     # record the new latency for each elink
     new_latency = {}
     # record the position at which BX0 was found for each elink (this needs to be the same for all elinks)
     found_BX0 = {}

     # reset links and set latency
     lc.set_latency([lcapture],latency)

     # set acquire
     lc.configure_acquire([lcapture],"linkreset_ECONt")

     # read latency
     lc.read_latency([lcapture])

     # capture on link reset econt
     lc.do_capture([lcapture],verbose=True)
     fc.request("link_reset_econt")
     fc.get_counter("link_reset_econt")
     
     # get captured data
     data = lc.get_captured_data([lcapture])[lcapture]
     
     # find BX0 in data and in link 0                                                                                                                                                                                                                                                                                      
     BX0_word = 0xf922f922
     BX0_rows,BX0_cols = (data == BX0_word).nonzero()
     logger.info('BX0 sync word found on columns %s',BX0_cols)
     logger.info('BX0 sync word found on rows %s',BX0_rows)
     
     try:
         assert len(BX0_rows) > 0
         assert (BX0_cols==0).nonzero()
     except AssertionError:
         logger.error('BX0 sync word not found anywhere or in link 0')
         for l in range(lc.nlinks[lcapture]):
             new_latency[l] = -1
         return new_latency,found_BX0,data
        
     # check that BX0 is found in the same position for all output links                                                                                                                                                                                                                                                   
     row_link_0 = (BX0_cols==0).nonzero()[0][0]
     for l in range(lc.nlinks[lcapture]):
         try:
             row_index = (BX0_cols==l).nonzero()[0][0]
         except:
             logger.warning('BX0 sync word not found for link %i'%l)
             new_latency[l] = -1
             continue
         
            try:
                assert BX0_rows[row_index] == BX0_rows[row_link_0]
                if bx0:
                    assert BX0_rows[row_index] == bx0[row_index]
                logger.info('Latency %i: %s found BX0 word at %d',latency[l],lcapture,BX0_rows[row_index])
                new_latency[l] = latency[l]
                found_BX0[l] = BX0_rows[row_index]
            except AssertionError:
                if bx0:
                    if BX0_rows[row_index] > bx0[row_index]:
			logger.warning('BX0 sync word for link %i found at %i, after reference bx0: %i'%(l,BX0_rows[row_index],bx0[row_index]))
                        new_latency[l] = latency[l]
                        found_BX0[l] = BX0_rows[row_index]
                    else:
                        logger.warning('BX0 sync word not found for link %i at (pos of link 0): %i or (pos of where bx0 was found for ASIC): %i'%(l,BX0_rows[row_link_0],bx0[row_index]))
                        new_latency[l] = -1
                else:
                    logger.warning('BX0 sync word not found for link %i at (pos of link 0): %i'%(l,BX0_rows[row_link_0]))
                    new_latency[l] = -1

        return new_latency,found_BX0,data


            
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

    logger = logging.getLogger('align:step:%s'%args.step)
    logger.setLevel('INFO')
    
    if args.step == "configure-IO":
        for io in args.io_names.split(','):
            if args.invertIO:
                io.configure_IO(invert=True)
            else:
                io.configure_IO()

    if args.step == "manual-IO":
        io.manual_IO(dev,"from","IO")

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
