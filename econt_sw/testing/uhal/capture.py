import uhal
import time
import argparse
import logging
logging.basicConfig()

from utils.uhal_config import *
import utils.link_capture as utils_lc
import utils.test_vectors as utils_tv
import utils.fast_command as utils_fc
import utils.stream_compare as utils_sc

logger = logging.getLogger('capture')
logger.setLevel('INFO')

def capture_lc(dev,lcaptures,nwords,mode,bx=0,nocsv=False,odir="./",fname="",nlinks=-1,phex=False,trigger=False):
    """
    Allows for captures in multiple lcs
    """
    fc_by_lfc = {'linkreset_ECONt': 'link_reset_econt',
                 'linkreset_ECONd': 'link_reset_econd',
                 'linkreset_ROCt': 'link_reset_roct',
                 'linkreset_ROCd': 'link_reset_rocd',
             }

    # make sure that fc is reset
    utils_fc.configure_fc(dev)

    for lcapture in lcaptures:
        if nlinks==-1:
            nlinks = input_nlinks if 'input' in lcapture else output_nlinks
        # configure acquisition
        utils_lc.configure_acquire(dev,lcapture,mode,nwords,nlinks,bx,verbose=False)
    
    # do link capture
    if mode in fc_by_lfc.keys():
        utils_lc.do_fc_capture(dev,fc_by_lfc[mode],lcaptures,verbose=False)
        time.sleep(0.001)
        counter = dev.getNode(names['fc-recv']+".counters.%s"%fc_by_lfc[mode]).read();
        dev.dispatch()
        logger.info('%s counter %i'%(fc_by_lfc[mode],counter))
    else:
        if mode == 'L1A' and not trigger:
            l1a_counter = dev.getNode(names['fc-recv']+".counters.l1a").read()
            dev.dispatch()
            logger.debug('L1A counter %i'%(int(l1a_counter)))
            utils_fc.send_l1a(dev)
            utils_lc.do_capture(dev,lcaptures,verbose=False)            
        else:
            utils_lc.do_capture(dev,lcaptures,verbose=False)

    # get captured data
    data = {}
    for lcapture in lcaptures:
        data[lcapture] = utils_lc.get_captured_data(dev,lcapture,nwords,nlinks,verbose=False)
    
        # save or print
        if not nocsv:
            utils_tv.save_testvector("%s/%s_%s.csv"%(odir,lcapture,fname), data[lcapture])
        if phex:
            datahex = utils_tv.fixed_hex(data[lcapture],8)
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

def disable_lc(dev,lcaptures,nlinks=-1):
    for lcapture in lcaptures:
        if nlinks==-1:
            inlinks = input_nlinks if 'input' in lcapture else output_nlinks
        utils_lc.disable_alignment(dev,lcapture,nlinks)

def syncword_lc(dev,lcaptures,syncword,nlinks=-1):
    for lcapture in lcaptures:
        if nlinks==-1:
            inlinks = input_nlinks if 'input' in lcapture else output_nlinks
        for l in range(inlinks):
            dev.getNode(names[lcapture]['lc']+".link"+str(l)+".align_pattern").write(int(syncword,16))
        dev.dispatch()

def compare_lc(dev,trigger=False,nlinks=-1,nwords=4095,nocsv=False,odir="./",fname="sc",phex=False,sleepTime=0.01,log=False):
    # stream compare just compares its two inputs.  
    # If they match, then it increments the word counter, and doesn't do anything else.
    # If they don't match, then it increments both the word and error counters, and, if it is set to do triggering, then it sets its "mismatch" output to 1 for one clock cycle (otherwise it is 0).
    if nlinks==-1:
        nlinks = output_nlinks
    lcaptures = ['lc-ASIC','lc-emulator']

    if trigger:
        # NOTE: before using trigger=True it is recommendable to check that the counters are not always increasing
        # otherwise we could get in some weird situations wiht link capture

        utils_fc.configure_fc(dev)
        # configure link captures to acquire on L1A
        for lcapture in lcaptures:
            utils_lc.configure_acquire(dev,lcapture,'L1A',nwords,nlinks,0,verbose=False)
        # set acquire to 1
        # you can set global.acquire to 1 whenever you like.  It will wait indefinitely for the next trigger
        utils_lc.do_capture(dev,lcaptures,verbose=False)

    # configure stream compare
    utils_sc.configure_compare(dev,nlinks,trigger)
    
    # log counters
    if log:
        while err_count <=0:
            err_count = utils_sc.reset_log_counters(dev,stime=sleepTime)
    else:
        err_count = utils_sc.reset_log_counters(dev,stime=sleepTime)

    # read data if error count > 0
    if err_count>0 and trigger:
        data = {}
        for lcapture in lcaptures:
            data[lcapture] = utils_lc.get_captured_data(dev,lcapture,nwords,nlinks,verbose=False)
            if not nocsv:
                utils_tv.save_testvector("%s/%s_%s.csv"%(odir,lcapture,fname), data[lcapture])
            if phex:
                datahex = utils_tv.fixed_hex(data[lcapture],8)
                for n in datahex: logger.info(','.join(n))

    # reset fc
    utils_fc.configure_fc(dev)

if __name__ == "__main__":
    """
    Capture and compare outputs
    - For capturing data, e.g:
    python testing/uhal/capture.py --capture --lc lc-ASIC --nwords 100 --mode BX --bx 0
    python testing/uhal/capture.py --capture --lc lc-ASIC  --nwords 100 --mode L1A
    
    Add:
    --nocsv: if do not want to save csv
    --odir: output directory for csv
    --fname: filename for csv
    --phex: if you want to print phex

    - For disabling automatic alignment, e.g.:
    python testing/uhal/capture.py --disable-align --lc lc-ASIC
    - For modifying sync word, e.g.:
    python testing/uhal/capture.py --sync 0x122 -lc lc-ASIC

    - For comparing outputs between lc-ASIC and lc-emulator:
    python testing/uhal/capture.py --compare --nlinks 13 --sleep 120
    python testing/uhal/capture.py --compare --nlinks 13 --trigger 

    Add:
    --sleep: sleeptime
    --trigger: trigger on a mistmatch
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE",default='INFO')
    parser.add_argument('--capture', action='store_true', default=False, help='capture data')
    parser.add_argument('--compare', action='store_true', default=False, help='compare counters in stream-compare')
    parser.add_argument('--disable-align',  action='store_true', dest='disablealign', default=False, help='disable automatic alignment')
    parser.add_argument('--sync', type=str, default=None, help='change sync word')

    parser.add_argument('--lc', type=str, default='lc-ASIC', choices=['lc-ASIC','lc-input','lc-emulator'], help='link capture to capture data')
    parser.add_argument('--mode', type=str, default='L1A', choices=['BX','L1A','linkreset_ECONt','linkreset_ECONd','linkreset_ROCt','linkreset_ROCd','orbitSync'], help='mode to capture')
    parser.add_argument('--bx', type=int, default=0, help='bx')
    parser.add_argument('--nwords', type=int, default=4095, help='number of words')
    parser.add_argument('--nlinks', type=int, default=-1, help='number of links')

    parser.add_argument('--nocsv', action='store_true', default=False, help='do not save captured data in csv format')
    parser.add_argument('--phex', action='store_true', default=False, help='print in hex format')
    parser.add_argument('--odir',dest="odir",type=str, default="./", help='output directory')
    parser.add_argument('--fname',dest="fname",type=str, default="", help='filename string')

    parser.add_argument('--sleep',dest='sleepTime',default=1,type=int,help='Time to wait between logging iterations')
    parser.add_argument('--trigger', action='store_true', default=False, help='Trigger on a mis-match')

    args = parser.parse_args()

    set_logLevel(args)
    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")

    try:
        logger.setLevel(args.logLevel)
    except ValueError:
        logging.error("Invalid log level")
        exit(1)

    if args.disablealign:
        disable_lc(dev,args.lc.split(','),args.nlinks)

    if args.sync:
        syncword_lc(dev,args.lc.split(','),args.sync,args.nlinks)

    if args.capture:
        capture_lc(dev,args.lc.split(','),args.nwords,args.mode,args.bx,args.nocsv,args.odir,args.fname,args.nlinks,args.phex)

    if args.compare:
        compare_lc(dev,trigger=args.trigger,nlinks=args.nlinks,nwords=args.nwords,nocsv=args.nocsv,odir=args.odir,fname=args.fname,phex=args.phex,sleepTime=args.sleepTime)
