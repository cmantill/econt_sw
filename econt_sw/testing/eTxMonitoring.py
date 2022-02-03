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

def read_testvector(fname,nlinks):
    import csv
    data = [[] for l in range(nlinks)]
    with open(fname) as f:
        csv_reader = csv.reader(f, delimiter=',')
        for i,row in enumerate(csv_reader):
            for l in range(nlinks):
                data[l].append(int(row[l],16))
    return np.array(data).T

def fixedHex(data,N):
    return np.vectorize(lambda d : '{num:0{width}x}'.format(num=d, width=N))(data)

def send_capture(lc="lc-ASIC",mode="BX",bx=0,nwords=4095,verbose=False):
    cmd = f'python testing/uhal/capture.py --capture --lc {lc} --mode {mode} --bx {bx} --nwords {nwords} --fname temp'
    if verbose:
        cmd += '--phex'
    os.system(cmd)

def set_PLL_phase_of_enable(phase=0):
    call_i2c(args_name='PLL_phase_of_enable_1G28',args_value=f'{phase}')
    
def scan_PLL_phase_of_enable(bx=40,nwords=100,goodPhase=0,verbose=True):
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
        logger.info(f'PLL_phase_of_enable_1G28 = {phase}')
        set_PLL_phase_of_enable(phase)
        
        # capture data at a fixed BX
        send_capture("lc-ASIC","BX",bx,nwords)
        data = read_testvector("lc-ASICtemp.csv",nlinks=13)
        scanData.append(data)

        dataHex = fixedHex(data,8)
        if verbose:
            logger.info('.'*50)
            logger.info(f'Raw Hex output ({phase} bit shift expected)')
            for n in dataHex: 
                logger.info(','.join(n))

        logger.info('BX number (first 5 bits)')
        print((data>>27&31))
        logger.info('.'*50)
        logger.info('BX number (first 5 bits), accounting for bit shift')
        print((data>>(27-phase))&31)
        logger.info('.'*50)

    expectedHeader = np.array(scanData[goodPhase]>>27 & 31).T[0]
    # this is missing BX0s...
    expectedHeader = np.append(expectedHeader,expectedHeader[-1]%15+1,axis=None)

    for phase in range(8):
        header=scanData[phase]>>(27-phase) & 31
        match=(header.T==expectedHeader[:-1]).all(axis=1)
        match_shift1=(header.T==expectedHeader[1:]).all(axis=1)
        state=np.zeros(13,dtype=int)
        state[match]=expectedHeader[0]
        state[match_shift1]=expectedHeader[1]
        print(phase, (match | match_shift1).all(), state)

    # go back to good phase
    set_PLL_phase_of_enable(goodPhase)

if __name__=='__main__':
    """
    ETX monitoring
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--scan', dest='scanPhaseEnable',default=False, action='store_true')
    parser.add_argument('--bx', type=int, default=40, help='bx')
    parser.add_argument('--nwords', type=int, default=4095, help='number of words')
    parser.add_argument('--good', type=int, default=0, help='good phase')
    args = parser.parse_args()

    if args.scanPhaseEnable:
        scan_PLL_phase_of_enable(args.bx,args.nwords,args.good)
