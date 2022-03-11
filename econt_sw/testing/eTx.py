from i2c import call_i2c
import numpy as np
import argparse
import time
import os

import logging
logger = logging.getLogger("eTx")
logger.setLevel(logging.INFO)
#ch = logging.StreamHandler()
#ch.setLevel(logging.INFO)
#logger.addHandler(ch)

from utils.uhal_config import output_nlinks
from utils.fast_command import FastCommands
from utils.link_capture import LinkCapture
from utils.test_vectors import TestVectors
from utils.stream_compare import StreamCompare

# initialize classes
fc = FastCommands()
lc = LinkCapture()
tv = TestVectors()
sc = StreamCompare()

def verbose_captured_data(data,csv=False,phex=False,odir="./",fname="temp",verbose=False):
    if csv:
        os.system(f'mkdir -p {odir}')
    for lcapture in data.keys():
        if csv:
            filename = f"{odir}/{lcapture}_{fname}.csv"
            if verbose:
                logger.info(f'Saving data from {lcapture} in {filename}')
            tv.save_testvector(filename,data[lcapture])
        if phex:
            logger.info(f'Printing {lcapture}')
            datahex = tv.fixed_hex(data[lcapture],8)
            for n in datahex: logger.info(','.join(n))

def capture(lcaptures,nwords=4095,
            mode="BX",bx=0,
            csv=False,phex=False,odir="./",fname="temp",
            trigger=False,verbose=False):
    # reset fc
    fc.configure_fc()

    # configure acquire
    lc.stop_continous_capture(lcaptures,verbose=verbose)
    lc.configure_acquire(lcaptures,mode,nwords=nwords,total_length=nwords,bx=bx,verbose=verbose)

    # do link capture
    if mode in lc.fc_by_lfc.keys():
        lc.do_capture(lcaptures,verbose)
        fc.request(lc.fc_by_lfc[mode],verbose)
        time.sleep(0.001)
        fc.get_counter(lc.fc_by_lfc[mode],verbose)
    else:
        if mode == 'L1A' and not trigger:
            fc.get_counter("l1a",verbose)
            lc.do_capture(lcaptures,verbose)
            fc.send_l1a()
            fc.get_counter("l1a",verbose)
        else:
            lc.do_capture(lcaptures,verbose)

    # get captured data
    data = lc.get_captured_data(lcaptures,nwords,verbose)

    # save or print
    verbose_captured_data(data,csv,phex,odir,fname,verbose)

    # reset fc
    fc.configure_fc()

    return data

def compare_lc(trigger=False,nlinks=-1,nwords=4095,
               csv=False,phex=False,odir="./",fname="sc",
               sleepTime=0.01,
               log=False,verbose=False):
    """Compare two link captures"""
    lcaptures = ['lc-ASIC','lc-emulator']
    if nlinks==-1:
        nlinks = output_nlinks

    if trigger:
        # NOTE: before using trigger=True it is recommendable to check that the counters are not always increasing
        # otherwise we could get in some weird situations wiht link capture

        # reset fc
        fc.configure_fc()

        # configure acquire
        lc.configure_acquire(lcaptures,'L1A',nwords,nwords,0,verbose)

        # set acquire to 1 (you can set global.acquire to 1 whenever you like.  It will wait indefinitely for the next trigger)
        lc.do_capture(lcaptures,verbose)

    # configure stream compare
    sc.configure_compare(nlinks,trigger)

    # log counters
    if log:
        while err_count <=0:
            err_count = sc.reset_log_counters(stime=sleepTime)
    else:
        err_count = sc.reset_log_counters(stime=sleepTime)

    # read data if error count > 0
    # trigger will capture 32 words prior to a mismatch identified by stream_compare
    data = None
    if err_count>0 and trigger:
        data = lc.get_captured_data(lcaptures,nwords,verbose)
        verbose_captured_data(data,csv,phex,odir,fname,verbose)

    # reset fc
    fc.configure_fc()

    return data

def event_daq(idir="",dtype="",
              i2ckeep=False,i2ckeys='ASIC,emulator',
              nwords=4095,nlinks=13,
              trigger=False,sleepTime=0.01,
              nocompare=False,
              yamlname="init"):
    """Automatize event DAQ"""
    # modify input or i2c registers if idir/dtype and/or yamlFile is given
    if idir!="" or dtype!="":
        logger.info(f"Loading input test vectors, dtype {dtype}, idir {idir}")
        tv.configure(dtype,idir)

        # modify slow control from that idir unless told so
        if idir!="" and not i2ckeep:
            yamlFile = f"{idir}/{yamlname}.yaml"
            logger.info(f"Loading i2c from {yamlFile} for {i2ckeys}")
            x=call_i2c(args_yaml=yamlFile, args_i2c=i2ckeys, args_write=True)

            # read nlinks from here
            try:
                nlinks = x['ASIC']['RW']['FMTBUF_ALL']['config_eporttx_numen']
            except:
                try:
                    nlinks = x['emulator']['RW']['FMTBUF_ALL']['config_eporttx_numen']
                except:
                    logger.error(f'Did not find info on config_eporttx_numen, keeping nlinks={nlinks}')
    if nocompare:
        return

    # check that IO and LC are aligned
    from check_block import check_align
    check_align('from-IO')
    check_align('lc-ASIC')

    # send compare command
    data = compare_lc(trigger=trigger,nlinks=nlinks,nwords=nwords,
                      csv=True,phex=False,odir="./",fname="sc",
                      sleepTime=sleepTime,log=False)

    # look at first rows of captured data
    if data is not None:
        for lcapture,data_lc in data.items():
            for i,row in enumerate(tv.fixed_hex(data_lc,8)[:40]):
                logger.info(f'{lcapture} {i}: '+",".join(map(str,list(row))))
            logger.info('.'*50)

def set_PLL_phase_of_enable(phase=0):
    call_i2c(args_name='PLL_phase_of_enable_1G28',args_value=f'{phase}')
    
def scan_PLL_phase_of_enable(bx=40,nwords=100,goodPhase=0,verbose=False):
    # send zeroes with headers
    os.system('python testing/uhal/test_vectors.py --dtype zeros')
    # set idle word to 0s
    call_i2c(args_name='FMTBUF_tx_sync_word',args_value=f'0')
    # set algorithm to threshold with high threshold, and enable all eTx
    call_i2c(args_name='MFC_ALGORITHM_SEL_DENSITY_algo_select,FMTBUF_eporttx_numen',args_value='0,13')
    call_i2c(args_name='ALGO_threshold_val_[0-47]',args_value='0x3fffff')

    scanData = []
    for phase in range(8):
        # set PLL_phase_of_enable
        set_PLL_phase_of_enable(phase)
        
        # capture data at a fixed BX
        data = capture(["lc-ASIC"],nwords=nwords,mode="BX",bx=bx)
        scanData.append(data["lc-ASIC"])

        if verbose:
            logger.info(f'PLL_phase_of_enable_1G28 = {phase}')
            logger.info('.'*50)
            logger.info(f'Raw Hex output ({phase} bit shift expected)')
            verbose_captured_data(data,phex=True)

    for i,data in enumerate(scanData):
        # logger.info(f'PLL_phase_of_enable_1G28 {i}, BX number (first 5 bits)')
        # print((data>>27&31))
        # logger.info('.'*50)
        logger.info(f'PLL_phase_of_enable_1G28 {i}, BX number (first 5 bits), accounting for bit shift')
        print((data>>(27-i))&31)
        logger.info('.'*50)

    expectedHeader = np.array(scanData[goodPhase]>>(27-goodPhase) & 31).T[0]
    # this is missing BX0s...
    expectedHeader = np.append(expectedHeader,expectedHeader[-1]%15+1,axis=None)

    for phase in range(8):
        header=scanData[phase]>>(27-phase) & 31
        match=(header.T==expectedHeader[:-1]).all(axis=1)
        match_shift1=(header.T==expectedHeader[1:]).all(axis=1)
        state=np.zeros(13,dtype=int)
        state[match]=expectedHeader[0]
        state[match_shift1]=expectedHeader[1]
        print(phase, np.count_nonzero(state)!=0, state)

    # go back to good phase
    set_PLL_phase_of_enable(goodPhase)

def PLL_phaseOfEnable_fixedPatternTest(nwords=40,verbose=False,algo='repeater'):
    # sending 1's in user_word 0 and 0s in user_word 1-3.
    # to enable pattern set CH_ALIGNER_*_patt_sel and CH_ALIGNER_*_patt_en to 1
    call_i2c(args_name='CH_ALIGNER_[0-11]_user_word_0,CH_ALIGNER_*_patt_*',args_value='[0xffffffff]*12,[1]*24')
    # call_i2c(args_name='CH_ALIGNER_[0-11]_user_word_1,CH_ALIGNER_[0-11]_user_word_2,CH_ALIGNER_[0-11]_user_word_3',args_value='[0]*12,[0]*12,[0]*12')

    if algo=='repeater':
        # set to repeater algorithm
        print('repeater')
        call_i2c(args_name='MFC_ALGORITHM_SEL_DENSITY_algo_select',args_value='3')
    else:
        # set to threshold algorithm
        call_i2c(args_name='MFC_ALGORITHM_SEL_DENSITY_algo_select',args_value='0')

    # manually override select value to 0 (so that you can see the consecutive bits in the output)
    x=call_i2c(args_name='CH_ALIGNER_[0-11]_select')
    selValues=','.join([str(x['ASIC']['RO'][f'CH_ALIGNER_{i}INPUT_ALL']['select']) for i in range(12)])

    call_i2c(args_name='CH_ALIGNER_[0-11]_sel_override_val',args_value='0')
    call_i2c(args_name='CH_ALIGNER_[0-11]_sel_override_en',args_value='1')

    for i_pll in range(8):
        call_i2c(args_name='PLL_phase_of_enable_1G28',args_value=f'{i_pll}')
        data = capture(["lc-ASIC"],nwords=nwords,mode="BX",bx=0)
        if verbose:
            verbose_captured_data(data,phex=True)
        data = data["lc-ASIC"]

        # only works for checking links 1-10,  eTx 0 has the header, so we don't expect 32 straight 1's, and eTx 11 & 12 are not used in repeater more
        goodLink=[]
        for i in range(1,11):
            x=''.join(np.vectorize(lambda x: f'{x:032b}')(data.T[i])[::-1])

            pattern=f'{(2**32-1):0128b}'*2
            if algo=='repeater' and i==10:
                # last link is not full, expect only 21 1's
                pattern=f'{(2**21-1):0128b}'*2

            if x.rfind(pattern)>-1:
                goodLink.append(True)
            else:
                goodLink.append(False)
                print(f'ERROR on eTx {i}, pattern not found')
                print(f'   {x[-256:]}')
        if np.array(goodLink).all():
            print('GOOD SETTING')

    call_i2c(args_name='PLL_phase_of_enable_1G28',args_value='0')
    call_i2c(args_name='CH_ALIGNER_[0-11]_sel_override_val',args_value=selValues)
    call_i2c(args_name='CH_ALIGNER_*_patt_*',args_value='[0]*24')
    return data

if __name__=='__main__':
    """
    ETX monitoring
    - For PLL Scan:
      python testing/eTx.py --scan --good 0 --bx 40 --nwords 100
    - For PLL Scan with fixed Pattern       
      python testing/eTx.py --scan --fixedPattern --algo repeater
   
    - For capturing data:
      python testing/eTx.py --capture --lc lc-input --mode BX --bx 0 --capture --nwords 511 --csv --verbose
      # or
      python testing/eTx.py --capture --lc lc-ASIC --mode linkreset_ECONt --capture --csv

    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--scan', dest='scanPhaseEnable', default=False, action='store_true', help="scan phase_of_enable values")
    parser.add_argument('--fixedPattern', dest='doFixedPatternTest',default=False, action='store_true')

    parser.add_argument('--capture', dest='capture', default=False, action='store_true', help="capture data on eTx")
    parser.add_argument('--compare', action='store_true', default=False, help='compare counters in stream-compare')
    parser.add_argument('--daq', dest='daq', default=False, action='store_true', help="take data")
    parser.add_argument('--disable-align', dest='disablealign', default=False, action='store_true', help='disable automatic alignment')
    parser.add_argument('--change-sync', dest='changesync', default=False, action='store_true', help='change sync word')
    parser.add_argument('--log', action='store_true', default=False, help='continuosly log counters in stream-compare')

    parser.add_argument('--good', type=int, default=0, help='good value of PLL_phase_of_enable')
    parser.add_argument('--algo', dest="algo", default="repeater", help="algorithm to use for fixedPattern test (repeater,threshold)")

    parser.add_argument('--lc', type=str, default='lc-ASIC', help='link capture to capture data, choices: lc-ASIC,lc-input,lc-emulator')
    parser.add_argument('--nwords', type=int, default=4095, help='number of words')
    parser.add_argument('--mode', type=str, default='BX', choices=['BX','L1A','linkreset_ECONt','linkreset_ECONd','linkreset_ROCt','linkreset_ROCd','orbitSync'], help='mode to capture')
    parser.add_argument('--bx', type=int, default=0, help='bx')
    parser.add_argument('--csv', action='store_true', default=False, help='save captured data in csv format')
    parser.add_argument('--phex', action='store_true', default=False, help='print in hex format')
    parser.add_argument('--odir', dest="odir",type=str, default="./", help='output directory for captured data')
    parser.add_argument('--fname',dest="fname",type=str, default="temp", help='filename string')
    parser.add_argument('--trigger', action='store_true', default=False, help='Trigger on a mis-match')
    parser.add_argument('--nlinks', type=int, default=13, help='number of links')

    parser.add_argument('--dtype', type=str, default="", help='dytpe (PRBS32,PRBS,PRBS28,debug,zeros)')
    parser.add_argument('--idir', dest="idir",type=str, default="", help='test vector directory')
    parser.add_argument('--i2ckeep', dest='i2ckeep',default=False, action='store_true', help="keep i2c configuration")
    parser.add_argument('--i2ckeys', dest='i2ckeys', type=str, default='ASIC,emulator', help="keys of i2c addresses(ASIC,emulator)")
    parser.add_argument('--yamlname', dest="yamlname",type=str, default="init", help='yaml filename in idir to load (exclude .yaml)')
    parser.add_argument('--sleep', dest='sleepTime', type=str, default='0.01',help='Time to wait between logging counters')
    parser.add_argument('--nocompare', action='store_true', default=False, help='Do not compare and just load the inputs')

    parser.add_argument('--contCapture', dest='continuousCapture', default=False, action='store_true', help="capture data on eTx continuously")

    parser.add_argument('--verbose', dest='verbose',default=False, action='store_true')
    args = parser.parse_args()

    
    if args.scanPhaseEnable:
        if args.doFixedPatternTest:
            data=PLL_phaseOfEnable_fixedPatternTest(nwords=12, verbose=args.verbose, algo=args.algo)
        else:
            scan_PLL_phase_of_enable(args.bx,args.nwords,args.good)
    elif args.capture:
        data = capture(args.lc.split(','),nwords=args.nwords,
                       mode=args.mode,bx=args.bx,
                       csv=args.csv,phex=args.phex,odir=args.odir,fname=args.fname,
                       trigger=args.trigger,verbose=args.verbose)
    elif args.compare:
        data = compare_lc(trigger=args.trigger,nlinks=args.nlinks,nwords=args.nwords,
                          csv=args.csv,phex=args.phex,odir=args.odir,fname=args.fname,
                          sleepTime=float(args.sleepTime),log=args.log)
    elif args.daq:
        event_daq(idir=args.idir,dtype=args.dtype,
                  i2ckeep=args.i2ckeep,i2ckeys=args.i2ckeys,
                  nwords=args.nwords,nlinks=args.nlinks,
                  trigger=args.trigger,sleepTime=float(args.sleepTime),
                  nocompare=args.nocompare,
                  yamlname=args.yamlname)
    elif args.disablealign:
        lc.disable_alignment(args.lc.split(','))
    elif args.changesync:
        lc.syncword(args.lc.split(','),args.sync)

    elif args.continuousCapture:
        try:
            data_prev=None
            while True:
                data = capture(['lc-ASIC','lc-emulator'],nwords=args.nwords,
                               mode='L1A',bx=args.bx,
                               csv=args.csv,phex=args.phex,odir=args.odir,fname=args.fname,
                               trigger=args.trigger,verbose=args.verbose)
                data_ASIC=data['lc-ASIC']
                data_em=data['lc-emulator']
                if not (data_ASIC==data_em).all():
                    logger.error('MISMATCH')
                    break
                if not data_prev is None:
                    if (data_prev==data_ASIC).all():
                        logger.info('No difference in data from last capture')
                    else:
                        logger.info('Different data from last capture')
                        break
                data_prev=data_ASIC
        except KeyboardInterrupt:
            pass
