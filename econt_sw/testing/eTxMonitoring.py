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

def send_capture(lc="lc-ASIC",mode="BX",bx=0,nwords=4095,verbose=False,asHex=False):
    cmd = f'python testing/uhal/capture.py --capture --lc {lc} --mode {mode} --bx {bx} --nwords {nwords} --fname temp'
    if verbose:
        cmd += '--phex'
    os.system(cmd)
    data = read_testvector("lc-ASICtemp.csv",nlinks=13,asHex=asHex)
    return data

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
        data = send_capture("lc-ASIC","BX",bx,nwords)
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
        data=send_capture(bx=0,nwords=nwords)
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

if __name__=='__main__':
    """
    ETX monitoring
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--scan', dest='scanPhaseEnable',default=False, action='store_true')
    parser.add_argument('--capture', dest='capture',default=False, action='store_true')
    parser.add_argument('--bx', type=int, default=12, help='bx')
    parser.add_argument('--nwords', type=int, default=4095, help='number of words')
    parser.add_argument('--good', type=int, default=0, help='good phase')
    parser.add_argument('--fixedPattern', dest='doFixedPatternTest',default=False, action='store_true')
    parser.add_argument('--algo', dest="algo", default="repeater", help="algorithm to use for fixedPattern test (repeater,threshold)")
    parser.add_argument('--verbose', dest='verbose',default=False, action='store_true')
    args = parser.parse_args()

    if args.scanPhaseEnable:
        if args.doFixedPatternTest:
            data=PLL_phaseOfEnable_fixedPatternTest(nwords=12, verbose=args.verbose, algo=args.algo)
        else:
            scan_PLL_phase_of_enable(args.bx,args.nwords,args.good)
    if args.capture:
        data=send_capture(bx=args.bx, nwords=args.nwords,asHex=True)
        if args.verbose:
            for n in data: print(','.join(n))



