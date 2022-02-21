from i2c import call_i2c
import numpy as np
import argparse
import os

import logging
logger = logging.getLogger("eTx")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)


from utils.fast_command import FastCommands
from utils.link_capture import LinkCapture
from utils.test_vectors import TestVectors
from utils.stream_compare import StreamCompare

# initialize classes
fc = FastCommands()
lc = LinkCapture()
tv = TestVectors()
sc = StreamCompare()

def capture(lcaptures,nwords,mode,bx=0,nocsv=False,odir="./",fname="",nlinks=-1,phex=False,trigger=False):
    # reset fc
    fc.configure_fc()

    # configure acquire
    lc.configure_acquire(lcaptures,mode,nwords,bx,verbose=False)

    # do link capture
    if mode in fc_by_lfc.keys():
        lc.do_fc_capture(fc_by_lfc[mode],lcaptures,verbose=False)
        time.sleep(0.001)
        fc.get_counter(fc_by_lfc[mode])
    else:
        if mode == 'L1A' and not trigger:
            fc.get_counter("l1a")
            fc.send_l1a()
            lc.do_capture(lcaptures,verbose=False)
        else:
            lc.do_capture(lcaptures,verbose=False)

    # get captured data
    data = lc.get_captured_data(lcaptures,nwords,verbose=False)    
    # save or print                                                                                                                                                                                                                                                                                                       
    if not nocsv:
        for lcapture in lcaptures:
            tv.save_testvector("%s/%s_%s.csv"%(odir,lcapture,fname), data[lcapture])
    if phex:
        datahex = tv.fixed_hex(data[lcapture],8)
        for n in datahex: logger.info(','.join(n))

    # reset fc
    fc.configure_fc()

def compare_lc(trigger=False,nlinks=-1,nwords=4095,nocsv=False,odir="./",fname="sc",phex=False,sleepTime=0.01,log=False):
    """                                                                                                                                                                                                                                                                                                                       
    Stream compare just compares its two inputs.                                                                                                                                                                                                                                                                              
    If they match, then it increments the word counter, and doesn't do anything else.                                                                                                                                                                                                                                         
    If they don't match, then it increments both the word and error counters, and, if it is set to do triggering, then it sets its "mismatch" output to 1 for one clock cycle (otherwise it is 0).                                                                                                                            
    """
    if nlinks==-1:
        nlinks = output_nlinks
    lcaptures = ['lc-ASIC','lc-emulator']

    if trigger:
        # NOTE: before using trigger=True it is recommendable to check that the counters are not always increasing                                                                                                                                                                                                            
        # otherwise we could get in some weird situations wiht link capture                                                                                                                                                                                                                                                   

        fc.configure_fc()

        # configure link captures to acquire on L1A                                                                                                                                                                                                                                                                           
        lc.configure_acquire(['lc-ASIC','lc-emulator'],'L1A',nwords,0,verbose=False)

        # set acquire to 1 (you can set global.acquire to 1 whenever you like.  It will wait indefinitely for the next trigger)                                                                                                                                                                                               
        lc.do_capture(lcaptures,verbose=False)

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
    if err_count>0 and trigger:
        data = {}
        for lcapture in lcaptures:
            data[lcapture] = lc.get_captured_data(lcapture,nwords,nlinks,verbose=False)
            if not nocsv:
                tv.save_testvector("%s/%s_%s.csv"%(odir,lcapture,fname), data[lcapture])
            if phex:
                datahex = tv.fixed_hex(data[lcapture],8)
                for n in datahex: logger.info(','.join(n))

    # reset fc                                                                                                                                                                                                                                                                                                                
    fc.configure_fc(dev)

if __name__ == "__main__":
    
def read_testvector(fname,nlinks,asHex=False):
    data = np.loadtxt(fname,delimiter=',',dtype=np.object)
    if not asHex:
        data = np.vectorize(int)(data,16)
    return data

def fixedHex(data,N):
    return np.vectorize(lambda d : '{num:0{width}x}'.format(num=d, width=N))(data)

def send_capture(lc="lc-ASIC",mode="BX",bx=0,nwords=4095,nlinks=13,fname="temp",verbose=False,asHex=False,sleepTime=0.01,
                 capture=False,compare=False,trigger=False):
    # remove old files
    lc_fname = f"{lc}_{fname}.csv"
    lc_emu_fname = f"lc-emulator_{fname}.csv"
    for lname in [lc_fname,lc_emu_fname]:
        try:
            os.remove(lname)
        except:
            continue

    cmd = f'python testing/uhal/capture.py --lc {lc} --mode {mode} --bx {bx} --nwords {nwords} --fname {fname} --nlinks {nlinks} --sleep {sleepTime}'
    if capture:
        cmd += ' --capture '
    if compare:
        cmd += ' --compare '
        if trigger:
            cmd += ' --trigger '
    if verbose:
        cmd += ' --phex '
    os.system(cmd)

    data_lc = None
    data_emu = None
    if os.path.exists(lc_fname):
        data_lc = read_testvector(lc_fname,nlinks=nlinks,asHex=asHex)
        if trigger and os.path.exists(lc_emu_fname):
            data_emu = read_testvector(lc_emu_fname,nlinks=nlinks,asHex=asHex)

    return data_lc,data_emu

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
        data,_ = send_capture("lc-ASIC","BX",bx,nwords,capture=True)
        scanData.append(data)

        dataHex = fixedHex(data,8)
        if verbose:
            logger.info(f'PLL_phase_of_enable_1G28 = {phase}')
            logger.info('.'*50)
            logger.info(f'Raw Hex output ({phase} bit shift expected)')
            for n in dataHex: 
                logger.info(','.join(n))

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
        print(i_pll)
        data,_=send_capture(bx=0,nwords=nwords,capture=True)
        datahex = fixedHex(data,8)
        print(datahex)

        # only works for checking links 1-10,  eTx 0 has the header, so we don't expect 32 straight 1's, and eTx 11 & 12 are not used in repeater more
        goodLink=[]
        if verbose:
            for n in fixedHex(data,8): print(','.join(n))
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

def event_daq(idir="",dtype="",i2ckeep=False,i2ckeys='ASIC,emulator',nwords=4095,trigger=False,nlinks=13,sleepTime=0.01,nocompare=False,yamlname="init"):
    """
    Automatize event DAQ.
    Only modify the input or i2c registers if idir/dtype and/or yamlFile is given.
    """
    # modify inputs
    if idir!="" or dtype!="":
        logger.info(f"Loading input test vectors, dtype {dtype}, idir {idir}")
        inputcmd = f"python testing/uhal/test_vectors.py"
        if idir !="": inputcmd += f" --idir {idir}"
        if dtype !="":  inputcmd += f" --dtype {dtype}"
        os.system(inputcmd)
        
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
    os.system('python testing/uhal/check_align.py --check --block from-IO --nlinks %i'%nlinks)
    os.system('python testing/uhal/check_align.py --check --block lc-ASIC --nlinks %i'%nlinks)

    # send compare command
    data_asic,data_emu = send_capture(compare=True,trigger=trigger,nwords=nwords,nlinks=nlinks,fname="temp",sleepTime=sleepTime)

    # look at first rows of captured data
    if (data_asic is not None) and (data_emu is not None):
        for i,row in enumerate(fixedHex(data_asic,8)[:40]):
            logger.info(f'lc-ASIC {i}: '+",".join(map(str,list(row))))
        logger.info('.'*50)
        for i,row in enumerate(fixedHex(data_emu,8)[:40]):
            logger.info(f'lc-emulator {i}: '+",".join(map(str,list(row))))
        logger.info('.'*50)

if __name__=='__main__':
    """
    ETX monitoring
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--scan', dest='scanPhaseEnable',default=False, action='store_true', help="scan phase_of_enable values")
    parser.add_argument('--capture', dest='capture',default=False, action='store_true', help="capture data on eTx")
    parser.add_argument('--daq', dest='daq',default=False, action='store_true', help="take data")
    parser.add_argument('--disable-align',  action='store_true', dest='disablealign', default=False, help='disable automatic alignment')
    parser.add_argument('--sync', type=str, default=None, help='change sync word')
    
    parser.add_argument('--bx', type=int, default=12, help='bx')
    parser.add_argument('--nwords', type=int, default=4095, help='number of words')
    parser.add_argument('--fname',dest="fname",type=str, default="", help='filename string')

    parser.add_argument('--good', type=int, default=0, help='good value of PLL_phase_of_enable')
    parser.add_argument('--fixedPattern', dest='doFixedPatternTest',default=False, action='store_true')
    parser.add_argument('--algo', dest="algo", default="repeater", help="algorithm to use for fixedPattern test (repeater,threshold)")

    parser.add_argument('--dtype', type=str, default="", help='dytpe (PRBS32,PRBS,PRBS28,debug,zeros)')
    parser.add_argument('--idir', dest="idir",type=str, default="", help='test vector directory')
    parser.add_argument('--i2ckeep', dest='i2ckeep',default=False, action='store_true', help="keep i2c configuration")
    parser.add_argument('--i2ckeys', dest='i2ckeys', type=str, default='ASIC,emulator', help="keys of i2c addresses(ASIC,emulator)")
    parser.add_argument('--yamlname', dest="yamlname",type=str, default="init", help='yaml filename in idir to load (exclude .yaml)')

    parser.add_argument('--sleep', dest='sleepTime', type=str, default='0.01',help='Time to wait between logging counters')
    parser.add_argument('--trigger', action='store_true', default=False, help='Trigger on a mis-match')
    parser.add_argument('--nocompare', action='store_true', default=False, help='Do not compare and just load the inputs')

    parser.add_argument('--verbose', dest='verbose',default=False, action='store_true')
    args = parser.parse_args()

    
    if args.scanPhaseEnable:
        if args.doFixedPatternTest:
            data=PLL_phaseOfEnable_fixedPatternTest(nwords=12, verbose=args.verbose, algo=args.algo)
        else:
            scan_PLL_phase_of_enable(args.bx,args.nwords,args.good)
    elif args.capture:
        data,_=send_capture(bx=args.bx, nwords=args.nwords,asHex=True,capture=True,fname=args.fname)
        if args.verbose:
            for row in data[:8]:
                logger.info('lc-ASIC: '+",".join(map(str,list(row))))
            logger.info('.'*50)

    elif args.daq:
        event_daq(idir=args.idir,dtype=args.dtype,i2ckeep=args.i2ckeep,i2ckeys=args.i2ckeys,nwords=args.nwords,trigger=args.trigger,sleepTime=float(args.sleepTime),nocompare=args.nocompare,yamlname=args.yamlname)
    elif args.disablealign:
        lc.disable_alignment(args.lc.split(','))
    elif args.sync:
        lc.syncword(args.lc.split(','),args.sync)
