from i2c import call_i2c
import numpy as np
import argparse
import os

from time import sleep
import datetime

import logging
logger = logging.getLogger("eRx")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)

def readSnapshot(i2c='ASIC',return_status=False):
    """
    Read registers that tell us about word alignment
    """
    x=call_i2c(args_yaml='configs/align_read.yaml', args_i2c=i2c)[i2c]['RO']
    snapshots=np.array([x[f'CH_ALIGNER_{i}INPUT_ALL']['snapshot'] + (x[f'CH_ALIGNER_{i}INPUT_ALL']['snapshot2']<<(16*8)) for i in range(12)])
    status=np.array([x[f'CH_ALIGNER_{i}INPUT_ALL']['status'] for i in range(12)])
    select=np.array([x[f'CH_ALIGNER_{i}INPUT_ALL']['select'] for i in range(12)])
    return snapshots, status, select

def readStatus(i2c='ASIC'):
    x=call_i2c(args_yaml='configs/align_read_status.yaml', args_i2c='ASIC')[i2c]['RO']
    for param in ['prbs_chk_err','orbsyn_fc_err','orbsyn_arr_err','orbsyn_hdr_err','align_seu_err','hdr_mm_err','snapshot_dv','pattern_match']:
        pararray = [x[f'CH_ALIGNER_{i}INPUT_ALL'][f'status_{param}'] for i in range(12)]
        logger.info(f"status {param} "+" ".join(map(str,pararray)))

def checkWordAlignment(verbose=True):
    """
    Check word alignment
    """
    snapshots_ASIC, status_ASIC, select_ASIC=readSnapshot('ASIC', True)
    snapshots_Emulator, status_Emulator, select_Emulator=readSnapshot('emulator', True)
    readStatus('ASIC')

    goodStatus=(status_ASIC==3).all()
    goodSelect=(select_ASIC<=64).all() & (select_ASIC>=32).all()
    # shift the snapshot by select bits, and look for accccccc9ccccccc at the end
    goodSnapshot = (((snapshots_ASIC >> select_ASIC) & 18446744073709551615) == 12451552248948640972).all()

    goodASIC = goodStatus & goodSelect & goodSnapshot
    goodEmulator=(status_Emulator==2).all() & (snapshots_Emulator==4237043671203321810880259700014693398528890914913710296268).all()

    if not (goodASIC):
        logger.error('Bad ASIC alignment')
        if not goodSelect: logger.error('select not in [32,64] range')
        elif not goodSnapshot: logger.error('no training pattern in snapshot')
        else: 
            logger.error('status!=3')
            readStatus('ASIC')

        for i in range(12):
            logger.info('eRx {:02n}:  status {:01n} / select {:03n} / snapshot {:048x}'.format(i,status_ASIC[i],select_ASIC[i], snapshots_ASIC[i]))
    else:
        if verbose:
            logger.info('Good ASIC alignment')
            for i in range(12):
                logger.info('eRx {:02n}:  status {:01n} / select {:03n} / snapshot {:048x}'.format(i,status_ASIC[i],select_ASIC[i], snapshots_ASIC[i])) 

    if not goodEmulator:
        logger.error('Bad emulator alignment')
        for i in range(12):
            logger.info('eRx {:02n}:  status {:01n} / select {:03n} / snapshot {:048x}'.format(i,status_Emulator[i],select_Emulator[i], snapshots_Emulator[i]))
    else:
        if verbose:
            logger.info('Good emulator alignment')
            for i in range(12):
                logger.info('eRx {:02n}:  status {:01n} / select {:03n} / snapshot {:048x}'.format(i,status_Emulator[i],select_Emulator[i], snapshots_Emulator[i]))
    return (goodStatus & goodSelect & goodEmulator)

def checkSnapshots(compare=True, verbose=False, bx=4):
    """
    Manually take a snapshot in BX bx
    """
    call_i2c(args_name='ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,CH_ALIGNER_*_per_ch_align_en,ALIGNER_snapshot_arm', args_value='1,1,[0]*12,0')
    call_i2c(args_name='ALIGNER_orbsyn_cnt_snapshot',args_value=f'{bx}')
    call_i2c(args_name='ALIGNER_snapshot_arm', args_value='1')
    snapshots,status,select=readSnapshot()
    call_i2c(args_name='ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,CH_ALIGNER_*_per_ch_align_en,ALIGNER_snapshot_arm', args_value='0,1,[1]*12,0')

    if verbose:
        output=''
        for i in range(12):
            output += '  CH {:02n}: {:048x}\n'.format(i,snapshots[i])
        logger.info(output)

    if compare:
        if len(np.unique(snapshots))==1:
            logger.info(f'All snapshots match : {hex(snapshots[0])}')
            return True
        else:
            shift = select-select.min()
            shiftedSnapshots=(snapshots>>shift)
            # do vertical vote to get 'correct' value
            vote=0
            for i in range(192):
                vote += (((shiftedSnapshots>>i)&1).sum()>6)<<i
            badSnapshots=np.argwhere(shiftedSnapshots!=vote)

            if len(badSnapshots)==0:
                logger.info(f'After shifting to accomodate select values, all snapshots match: {hex(vote)}')
            else:
                errors={i: hex(snapshots[i]) for i in badSnapshots.flatten()}
                logger.error(f'Vote of snapshots is {hex(vote)}, errors in snapshots : {errors}')
            return False

def get_HDR_MM_CNTR(previous=None):
    """
    Get hdr mm cntr
    """
    x=call_i2c(args_name='CH_ALIGNER_*_hdr_mm_cntr')
    counts=np.array([x['ASIC']['RO'][f'CH_ALIGNER_{i}INPUT_ALL']['hdr_mm_cntr'] for i in range(12)])
    if previous is None:
        return counts

    agreement = (counts==previous) & ~(counts==65535)
    if agreement.all():
        logger.info(f'Good counters {counts}')
    else:
        increase=np.argwhere((counts>previous) | (counts==65535)).flatten()
        logger.error(f'Increase in channels {increase}: {counts-previous}')
        logger.error(f'          previous values {previous}')
        logger.error(f'          current values {counts}')
    return counts

def statusLogging(sleepTime=120, N=30, snapshot=False, tag=""):
    """
    Log hdr mm cntrs
    """
    
    hdr_mm_counters = []

    x=get_HDR_MM_CNTR()
    hdr_mm_counters.append(x)

    for i in range(N):
        sleep(sleepTime)
        print('-'*40)
        print(datetime.datetime.now())
        if snapshot:
            checkSnapshots()
        x=get_HDR_MM_CNTR(x)
        hdr_mm_counters.append(list(x))

    if args.tag!="":
        import csv
        with open(f"hdr_mm_cntr_{tag}.csv", 'w') as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerow([f'CH_{ch}' for ch in range(12)])
            for j in hdr_mm_counters:
                writer.writerow(j)

if __name__=='__main__':
    """
    ERX monitoring
    - To log hdr mm cntrs over a period of time: 
      python3 testing/eRxMonitoring.py --logging --sleep 120 -N 10
    - To take a snapshot manually at one bx
      python3 testing/eRxMonitoring.py --snapshot --bx 4 
    - To check word alignment
      python3 testing/eRxMonitoring.py --alignment --verbose
    - To get HDR MM CNTR
      python3 testing/eRxMonitoring.py --hdrMM
    - To do PRBS scan
      python3 testing/eRxMonitoring.py --prbs --sleep 1
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('--logging', dest='runLogging',default=False, action='store_true')
    parser.add_argument('--snapshot', dest='getSnapshot',default=False, action='store_true')
    parser.add_argument('--hdrMM', dest='getHdrMM',default=False, action='store_true')
    parser.add_argument('--prbs', dest='prbsPhaseScan',default=False, action='store_true')
    parser.add_argument('--alignment', dest='checkWordAlignment',default=False, action='store_true')
    parser.add_argument('-N',dest='N',default=1,type=int,help='Number of iterations to run')
    parser.add_argument('--sleep',dest='sleepTime',default=120,type=int,help='Time to wait between logging iterations')
    parser.add_argument('--tag',dest='tag',default="test",type=str,help="Tag to save hdr mm cntr histogram")
    parser.add_argument('--verbose', dest='verbose',default=False, action='store_true')
    parser.add_argument('--threshold', dest='threshold',default=0,type=int, help='Threshold of number of allowed errors')
    parser.add_argument('--bx', dest='bx',default=4,type=int, help='BX to take snapshot in')

    args = parser.parse_args()

    if args.runLogging:
        statusLogging(sleepTime=args.sleepTime, N=args.N, snapshot=args.getSnapshot, tag=args.tag)

    elif args.getSnapshot:
        checkSnapshots(verbose=True, bx=args.bx)

    elif args.checkWordAlignment:
        checkWordAlignment(verbose=args.verbose)

    elif args.getHdrMM:
        x=get_HDR_MM_CNTR()
        logger.info(f'hdr_mm_cntr '+" ".join(map(str,list(x))))

    elif args.prbsPhaseScan:
        from PRBS import scan_prbs
        args.i2c='ASIC'
        args.prbs=32
        err_counts, best_setting = scan_prbs(args,range(0,12),True)
