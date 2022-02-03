import uhal
import time
import argparse
import logging
logging.basicConfig()

from utils.uhal_config import *
import utils.link_capture as utils_lc
import utils.test_vectors as utils_tv
import utils.fast_command as utils_fc

logger = logging.getLogger('capture')
logger.setLevel('INFO')

def capture_lc(dev,lcapture,nwords,mode,bx=0,csv=True,odir="./",fname="",nlinks=-1,phex=False):
    # make sure that fc is reset
    utils_fc.configure_fc(dev)

    if nlinks==-1:
        nlinks = input_nlinks if 'input' in lcapture else output_nlinks

    # configure acquisition
    utils_lc.configure_acquire(dev,lcapture,mode,nwords,nlinks,bx,verbose=False)
    
    # do link capture
    if mode == "linkreset_ECONt":
        utils_lc.do_fc_capture(dev,"link_reset_econt",lcapture,verbose=False)
        time.sleep(0.001)
        lrc = dev.getNode(names['fc-recv']+".counters.link_reset_econt").read();
        dev.dispatch()
        logger.info('link reset econt counter %i'%lrc)
    elif mode =="linkreset_ROCt":
        utils_lc.do_fc_capture(dev,"link_reset_roct",lcapture,verbose=False)
        time.sleep(0.001)
        lrc = dev.getNode(names['fc-recv']+".counters.link_reset_roct").read();
        dev.dispatch()
        logger.info('link reset roct counter %i'%lrc)
    elif mode == "L1A":
        l1a_counter = dev.getNode(names['fc-recv']+".counters.l1a").read()
        dev.dispatch()
        logger.debug('L1A counter %i'%(int(l1a_counter)))
        utils_fc.send_l1a(dev)
    else:
        utils_lc.do_capture(dev,lcapture,verbose=False)

    # get captured data
    data = utils_lc.get_captured_data(dev,lcapture,nwords,nlinks,verbose=False)
    
    # save or print
    if csv:
        utils_tv.save_testvector("%s/%s%s.csv"%(odir,lcapture,fname), data)
    if phex:
        datahex = utils_tv.fixed_hex(data,8)
        for n in datahex: logger.info(','.join(n))

    # reset fc
    utils_fc.configure_fc(dev)

def reset_lc(dev,lcapture,syncword=""):
    sync_patterns = {
        'lc-ASIC': 0x122,
        'lc-emulator': 0x122,
        'lc-input': 0xaccccccc,
    }
    if syncword!="":
        sync_patterns[lcapture] = syncword

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

def disable_lc(dev,lcapture,nlinks=-1):
    if nlinks==-1:
        nlinks = input_nlinks if 'input' in lcapture else output_nlinks
    utils_lc.disable_alignment(dev,lcapture,nlinks)

def syncword_lc(dev,lcapture,syncword,nlinks=-1):
    if nlinks==-1:
        nlinks = input_nlinks if 'input' in lcapture else output_nlinks
    for l in range(nlinks):
        dev.getNode(names[lcapture]['lc']+".link"+str(l)+".align_pattern").write(int(syncword,16))
    dev.dispatch()

def compare_counters(dev,sleepTime=0.001):
    dev.getNode(names['stream_compare']+".control.reset").write(0x1) # start the counters from zero                                                                                                                                                                         
    time.sleep(sleepTime)
    dev.getNode(names['stream_compare']+".control.latch").write(0x1) # latch the counters                                                                                                                                                                                   
    dev.dispatch()
    word_count = dev.getNode(names['stream_compare']+".word_count").read()
    err_count = dev.getNode(names['stream_compare']+".err_count").read()
    dev.dispatch()
    logger.info('Stream compare, word count %d, error count %d'%(word_count,err_count))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE",default='INFO')
    parser.add_argument('--capture', action='store_true', default=False, help='capture data')
    parser.add_argument('--csv', action='store_true', default=True, help='save captured data in csv format')
    parser.add_argument('--phex', action='store_true', default=False, help='print in hex format')
    parser.add_argument('--odir',dest="odir",type=str, default="./", help='output directory')
    parser.add_argument('--fname',dest="fname",type=str, default="", help='filename string')
    parser.add_argument('--lc', type=str, default='lc-ASIC', help='link capture to capture data')
    parser.add_argument('--mode', type=str, default='L1A', help='options (BX,linkreset_ECONt,linkreset_ECONd,linkreset_ROCt,linkreset_ROCd,L1A,orbitSync)')
    parser.add_argument('--bx', type=int, default=0, help='bx')
    parser.add_argument('--nwords', type=int, default=4095, help='number of words')
    parser.add_argument('--nlinks', type=int, default=-1, help='number of links')
    
    args = parser.parse_args()

    set_logLevel(args)
    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")

    try:
        logger.setLevel(args.logLevel)
    except ValueError:
        logging.error("Invalid log level")
        exit(1)

    if args.capture:
        capture_lc(dev,args.lc,args.nwords,args.mode,args.bx,args.csv,args.odir,args.fname,args.nlinks,args.phex)
