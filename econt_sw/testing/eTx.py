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
        data = send_capture("lc-ASIC","BX",bx,nwords,capture=True)
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
        data=send_capture(bx=0,nwords=nwords,capture=True)
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

def event_daq(idir="",dtype="",i2ckeep=False,i2ckeys='ASIC,emulator',nwords=4095,trigger=False,nlinks=13,sleepTime=0.01):
    """
    Automatize event DAQ.
    Only modify the input or i2c registers if idir/dtype and/or yamlFile is given.
    """
    # check that link capture and IO are aligned
    os.system('python testing/uhal/check_align.py --check --block from-IO')
    os.system('python testing/uhal/check_align.py --check --block lc-ASIC')

    # modify inputs
    if idir!="" or dtype!="":
        logger.info(f"Loading input test vectors, dtype {dtype}, idir {idir}")
        inputcmd = f"python testing/uhal/test_vectors.py"
        if idir !="": inputcmd += f" --idir {idir}"
        if dtype !="":  inputcmd += f" --dtype {dtype}"
        os.system(inputcmd)
        
        # modify slow control from that idir unless told so
        if idir!="" and not i2ckeep:
            yamlFile = f"{idir}/init.yaml"
            logger.info(f"Loading i2c from {yamlFile} for {i2ckeys}")
            x=call_i2c(args_yaml=yamlFile, args_i2c=i2ckeys, args_write=True)
            
            # read nlinks from here
            try:
                nlinks = x['ASIC']['RW']['FMTBUF_ALL']['config_eporttx_numen']
            except:
                logger.error(f'Did not find info on config_eporttx_numen, keeping nlinks={nlinks}')

    # send compare command
    data_asic,data_emu = send_capture(compare=True,trigger=trigger,nwords=nwords,nlinks=nlinks,fname="temp",sleepTime=sleepTime)

    # look at first rows of captured data
    if (data_asic is not None) and (data_emu is not None):
        for row in fixedHex(data_asic,8)[:10]:
            logger.info('lc-ASIC: '+",".join(map(str,list(row))))
        logger.info('.'*50)
        for row in fixedHex(data_emu,8)[:10]:
            logger.info('lc-emulator: '+",".join(map(str,list(row))))
        logger.info('.'*50)

if __name__=='__main__':
    """
    ETX monitoring
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--scan', dest='scanPhaseEnable',default=False, action='store_true', help="scan phase_of_enable values")
    parser.add_argument('--capture', dest='capture',default=False, action='store_true', help="capture data on eTx")
    parser.add_argument('--daq', dest='daq',default=False, action='store_true', help="take data")

    parser.add_argument('--bx', type=int, default=12, help='bx')
    parser.add_argument('--nwords', type=int, default=4095, help='number of words')

    parser.add_argument('--good', type=int, default=0, help='good value of PLL_phase_of_enable')
    parser.add_argument('--fixedPattern', dest='doFixedPatternTest',default=False, action='store_true')
    parser.add_argument('--algo', dest="algo", default="repeater", help="algorithm to use for fixedPattern test (repeater,threshold)")

    parser.add_argument('--dtype', type=str, default="", help='dytpe (PRBS32,PRBS,PRBS28,debug,zeros)')
    parser.add_argument('--idir', dest="idir",type=str, default="", help='test vector directory')
    parser.add_argument('--i2ckeep', dest='i2ckeep',default=False, action='store_true', help="keep i2c configuration")
    parser.add_argument('--i2ckeys', dest='i2ckeys', type=str, default='ASIC,emulator', help="keys of i2c addresses(ASIC,emulator)")

    parser.add_argument('--sleep',dest='sleepTime',default=1,type=int,help='Time to wait between logging counters')
    parser.add_argument('--trigger', action='store_true', default=False, help='Trigger on a mis-match')

    parser.add_argument('--verbose', dest='verbose',default=False, action='store_true')
    args = parser.parse_args()

    if args.scanPhaseEnable:
        if args.doFixedPatternTest:
            data=PLL_phaseOfEnable_fixedPatternTest(nwords=12, verbose=args.verbose, algo=args.algo)
        else:
            scan_PLL_phase_of_enable(args.bx,args.nwords,args.good)
    elif args.capture:
        data=send_capture(bx=args.bx, nwords=args.nwords,asHex=True,capture=True)
        if args.verbose:
            for n in data: print(','.join(n))
    elif args.daq:
        event_daq(idir=args.idir,dtype=args.dtype,i2ckeep=args.i2ckeep,i2ckeys=args.i2ckeys,nwords=args.nwords,trigger=args.trigger,sleepTime=args.sleepTime)


