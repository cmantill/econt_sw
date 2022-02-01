from i2c import call_i2c
import numpy as np
import argparse
import os

def readSnapshot(i2c='ASIC',return_status=False):
    x=call_i2c(args_yaml='configs/align_read.yaml', args_i2c=i2c)
    snapshots=np.array([x[i2c]['RO'][f'CH_ALIGNER_{i}INPUT_ALL']['snapshot'] + (x[i2c]['RO'][f'CH_ALIGNER_{i}INPUT_ALL']['snapshot2']<<(16*8)) for i in range(12)])
    status=np.array([x[i2c]['RO'][f'CH_ALIGNER_{i}INPUT_ALL']['status'] for i in range(12)])
    select=np.array([x[i2c]['RO'][f'CH_ALIGNER_{i}INPUT_ALL']['select'] for i in range(12)])
    if return_status:
        return snapshots, status, select
    else:
        return snapshots

def checkWordAlignment(verbose=True):
    snapshots_ASIC, status_ASIC, select_ASIC=readSnapshot('ASIC', True)
    snapshots_Emulator, status_Emulator, select_Emulator=readSnapshot('emulator', True)

    goodStatus=(status_ASIC==3).all()
    goodSelect=(select_ASIC<=64).all() & (select_ASIC>=32).all()
    goodEmulator=(status_Emulator==2).all() & (snapshots_Emulator==4237043671203321810880259700014693398528890914913710296268).all()

    if not (goodStatus & goodSelect):
        print('ERROR: bad ASIC alignment')
        for i in range(12):
            print('eRx {:02n}:  status {:01n} / select {:03n} / snapshot {:048x}'.format(i,status_ASIC[i],select_ASIC[i], snapshots_ASIC[i]))
    else:
        if verbose:
            print('Good ASIC alignment')
            for i in range(12):
                print('eRx {:02n}:  status {:01n} / select {:03n} / snapshot {:048x}'.format(i,status_ASIC[i],select_ASIC[i], snapshots_ASIC[i]))

    if not goodEmulator:
        print('ERROR: bad emulator alignment')
        for i in range(12):
            print('eRx {:02n}:  status {:01n} / select {:03n} / snapshot {:048x}'.format(i,status_Emulator[i],select_Emulator[i], snapshots_Emulator[i]))
    else:
        if verbose:
            print('Good emulator alignment')
            for i in range(12):
                print('eRx {:02n}:  status {:01n} / select {:03n} / snapshot {:048x}'.format(i,status_Emulator[i],select_Emulator[i], snapshots_Emulator[i]))
    return (goodStatus & goodSelect & goodEmulator)

def checkSnapshots(compare=True, verbose=False, bx=4):
    call_i2c(args_name='ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,CH_ALIGNER_*_per_ch_align_en,ALIGNER_snapshot_arm', args_value='1,1,[0]*12,0')
    call_i2c(args_name='ALIGNER_orbsyn_cnt_snapshot',args_value=f'{bx}')
    call_i2c(args_name='ALIGNER_snapshot_arm', args_value='1')
    snapshots=readSnapshot()
    call_i2c(args_name='ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,CH_ALIGNER_*_per_ch_align_en,ALIGNER_snapshot_arm', args_value='0,1,[1]*12,0')


    if verbose:
        output=''
        for i in range(12):
            output += '  CH {:02n}: {:048x}\n'.format(i,snapshots[i])
        print(output)
    if compare:
        if len(np.unique(snapshots))==1:
            print(f'All snapshots match : {hex(snapshots[0])}')
            return True
        else:
            #do vertical vote to get 'correct' value
            vote=0
            for i in range(192):
                vote += (((snapshots>>i)&1).sum()>6)<<i
            badSnapshots=np.argwhere(snapshots!=vote)
            errors={i: hex(snapshots[i]) for i in badSnapshots.flatten()}
            print(f'ERROR, vote of snapshots is {hex(vote)}, errors in snapshots : {errors}')

            return False



def get_HDR_MM_CNTR(previous=None):
    x=call_i2c(args_name='CH_ALIGNER_*_hdr_mm_cntr')

    
    counts=np.array([x['ASIC']['RO'][f'CH_ALIGNER_{i}INPUT_ALL']['hdr_mm_cntr'] for i in range(12)])

    if previous is None:
        return counts

    agreement = (counts==previous) & ~(counts==65535)

    if agreement.all():
        print(f'Good counters {counts}')
    else:
        increase=np.argwhere((counts>previous) | (counts==65535)).flatten()
        print(f'ERROR, Increase in channels {increase}: {counts-previous}')
        print(f'          previous values {previous}')
        print(f'           current values {counts}')

    return counts




from time import sleep
import datetime

def statusLogging(sleepTime=120, N=30):
    x=get_HDR_MM_CNTR()

    for i in range(N):
        sleep(sleepTime)
        print('-'*40)
        print(datetime.datetime.now())
        checkSnapshots()
        x=get_HDR_MM_CNTR(x)




def prbsScan(sleepTime=5, threshold=0, verbose=False):
    os.system('python testing/uhal/align_on_tester.py --step test-data --dtype PRBS')

    call_i2c(args_name=f'EPRXGRP_TOP_trackMode',args_value='0')
    call_i2c(args_name=f'CH_ALIGNER_[0-11]_prbs28_en',args_value='0')

    errCounts=[]
    for i in range(16):
        call_i2c(args_name='CH_ALIGNER_[0-11]_prbs_chk_en', args_value='[0]*12')
        call_i2c(args_name=f'MISC_rw_ecc_err_clr',args_value='1')
        call_i2c(args_name='CH_EPRXGRP_[0-11]_phaseSelect',args_value=f'{i}')
        call_i2c(args_name='CH_ALIGNER_[0-11]_prbs_chk_en', args_value='[1]*12')
        call_i2c(args_name=f'MISC_rw_ecc_err_clr',args_value='0')
        sleep(sleepTime)
        x=call_i2c(args_name=f'CH_ALIGNER_[0-11]_prbs_chk_err_cnt')
        errCounts.append([x['ASIC']['RO'][f'CH_ALIGNER_{j}INPUT_ALL']['prbs_chk_err_cnt'] for j in range(12)])
        if verbose:
            print(' phaseSelect: {:02n}, prbs_chk_err_cnt: {}'.format(i,str(errCounts[-1])))
    errCounts = np.array(errCounts).astype(int)
    if verbose:
        print('PhaseScanOutputs:')
        print(errCounts)

    countsWindow=[]
    for i in range(15):
        #add counts over 3 setting window, summing i, i+1, and i-1 (mod 15)
        countsWindow.append( errCounts[i] + errCounts[(i-1)%15] + errCounts[(i+1)%15] )
    countsWindow=np.array(countsWindow)

    if verbose:
        print()
        print('Error Counts over 3 setting window:')
        print(countsWindow)
    countsWindow[ errCounts[:-1]>threshold ] = 255*3
    bestSetting=np.array(countsWindow).argmin(axis=0)
    if verbose:
        print()
        print('Best phase settings: ', bestSetting)
    return errCounts, bestSetting



if __name__=='__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--logging', dest='runLogging',default=False, action='store_true')
    parser.add_argument('--snapshot', dest='getSnapshot',default=False, action='store_true')
    parser.add_argument('--hdrMM', dest='getHdrMM',default=False, action='store_true')
    parser.add_argument('--prbs', dest='prbsPhaseScan',default=False, action='store_true')
    parser.add_argument('--alignment', dest='checkWordAlignment',default=False, action='store_true')
    parser.add_argument('-N',dest='N',default=1,type=int,help='Number of iterations to run')
    parser.add_argument('--sleep',dest='sleepTime',default=120,type=int,help='Time to wait between logging iterations')
    parser.add_argument('--verbose', dest='verbose',default=False, action='store_true')
    parser.add_argument('--threshold', dest='threshold',default=0,type=int, help='Threshold of number of allowed errors')

    args = parser.parse_args()

    if args.runLogging:
        statusLogging(sleepTime=args.sleepTime, N=args.N)

    if args.getSnapshot:
        checkSnapshots(verbose=True)

    if args.checkWordAlignment:
        checkWordAlignment(verbose=args.verbose)

    if args.getHdrMM:
        x=get_HDR_MM_CNTR()
        print(x)

    if args.prbsPhaseScan:
        x=prbsScan(sleepTime=args.sleepTime, threshold=args.threshold, verbose=args.verbose)
        
