from i2c import call_i2c
import numpy as np
import argparse
import os

from time import sleep
import datetime
from utils.fast_command import FastCommands
from utils.link_capture import LinkCapture
from utils.test_vectors import TestVectors

import logging
logger = logging.getLogger("eRx")
logger.setLevel(logging.INFO)
    
def readSnapshot(i2c='ASIC',return_status=False):
    """
    Read registers that tell us about word alignment
    """
    x=call_i2c(args_yaml='configs/align_read.yaml', args_i2c=i2c)[i2c]['RO']
    snapshots=np.array([x[f'CH_ALIGNER_{i}INPUT_ALL']['snapshot'] + (x[f'CH_ALIGNER_{i}INPUT_ALL']['snapshot2']<<(16*8)) for i in range(12)])
    status=np.array([x[f'CH_ALIGNER_{i}INPUT_ALL']['status'] for i in range(12)])
    select=np.array([x[f'CH_ALIGNER_{i}INPUT_ALL']['select'] for i in range(12)])
    return snapshots, status, select

def readStatus(i2c='ASIC',verbose=True):
    x=call_i2c(args_yaml='configs/align_read_status.yaml', args_i2c='ASIC')[i2c]['RO']
    for param in ['prbs_chk_err','orbsyn_fc_err','orbsyn_arr_err','orbsyn_hdr_err','align_seu_err','hdr_mm_err','snapshot_dv','pattern_match']:
        pararray = [x[f'CH_ALIGNER_{i}INPUT_ALL'][f'status_{param}'] for i in range(12)]
        if verbose:
            logger.info(f"status {param} "+" ".join(map(str,pararray)))

def i2cSnapshot(bx=4):
    call_i2c(args_name='ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,CH_ALIGNER_*_per_ch_align_en,ALIGNER_snapshot_arm', args_value='1,1,[0]*12,0')
    call_i2c(args_name='ALIGNER_orbsyn_cnt_snapshot,ALIGNER_snapshot_arm',args_value=f'{bx},1')
    snapshots,status,select=readSnapshot()
    call_i2c(args_name='ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,CH_ALIGNER_*_per_ch_align_en,ALIGNER_snapshot_arm', args_value='0,1,[1]*12,0')
    return snapshots, status, select

def overrideSelect(select_ASIC):
    print('Overriding select settings with ',select_ASIC)
    call_i2c(args_name='CH_ALIGNER_[0-11]_sel_override_en',args_value='1')
    select_values = ','.join('{}'.format(*k) for k in enumerate(select_ASIC))
    call_i2c(args_name='CH_ALIGNER_[0-11]_sel_override_val',args_value=select_values)

def linkResetAlignment(snapshotBX=4, orbsyncVal=0, override=True, check=True, verbose=False, delay=None):
    """
    Performs automatic alignment sequence.
    Sets minimum i2c settings required for alignment, then issues a link_reset_roct fast command
    """

    call_i2c(args_name='CH_ALIGNER_[0-11]_per_ch_align_en',args_value='1',args_i2c='ASIC,emulator')
    call_i2c(args_name='CH_ALIGNER_[0-11]_sel_override_en,CH_ALIGNER_[0-11]_patt_en,CH_ALIGNER_[0-11]_prbs_chk_en',
             args_value='0', args_i2c='ASIC,emulator')
    call_i2c(args_name='ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,ALIGNER_snapshot_arm,ALIGNER_orbsyn_cnt_snapshot,ALIGNER_orbsyn_cnt_load_val,ALIGNER_match_pattern_val,ALIGNER_match_mask_val',
             args_value=f'0,1,1,{snapshotBX},{orbsyncVal},0x9cccccccaccccccc,0',
             args_i2c='ASIC,emulator')

    if not delay is None:
        from utils.asic_signals import ASICSignals
        signals=ASICSignals()
        signals.set_delay(delay)

    fc=FastCommands()
    fc.configure_fc()
    fc.set_bx("link_reset_roct",3500)
    fc.request('link_reset_roct')
    
    if check:
        status,select_ASIC=checkWordAlignment(verbose=verbose,ASIC_only=False)

        if status==False:
            checkWordAlignment(verbose=True,ASIC_only=False)
        else:
            print('Good Alignment')
            if override:
                overrideSelect(select_ASIC)
                
def checkWordAlignment(verbose=True, ASIC_only=False):
    """Check word alignment"""
    snapshots_ASIC, status_ASIC, select_ASIC=readSnapshot('ASIC', True)
    
    if not ASIC_only: snapshots_Emulator, status_Emulator, select_Emulator=readSnapshot('emulator', True)

    #readStatus('ASIC',verbose)

    goodStatus=((status_ASIC&3)==3).all()
    goodSelect=(select_ASIC<=64).all() & (select_ASIC>=32).all()

    #if only checking alignment of ASIC, it doesn't matter if we are within this range, only that we get good status
    if ASIC_only: goodSelect=True

    # shift the snapshot by select bits, and look for 9ccccccc at the end
    goodSnapshot = (((snapshots_ASIC >> select_ASIC) & 0xffffffff) == 0x9ccccccc).all()
    
    goodASIC = goodStatus & goodSelect & goodSnapshot
    if ASIC_only: 
        goodEmulator=True
    else:
        goodEmulator=(status_Emulator==2).all() & (snapshots_Emulator==0xacccccccacccccccacccccccaccccccc9cccccccaccccccc).all()

    if not (goodASIC) and verbose:
        logger.error('Bad ASIC alignment')
        if not goodSelect: logger.error('select not in [32,64] range')
        elif not goodSnapshot:
            logger.error('no training pattern in snapshot')
            if verbose:
                print(((snapshots_ASIC >> select_ASIC) & 0xffffffff) == 0x9ccccccc)
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

    if not ASIC_only:
        if not goodEmulator and verbose:
            logger.error('Bad emulator alignment')
            for i in range(12):
                logger.info('eRx {:02n}:  status {:01n} / select {:03n} / snapshot {:048x}'.format(i,status_Emulator[i],select_Emulator[i], snapshots_Emulator[i]))
        else:
            if verbose:
                logger.info('Good emulator alignment')
                for i in range(12):
                    logger.info('eRx {:02n}:  status {:01n} / select {:03n} / snapshot {:048x}'.format(i,status_Emulator[i],select_Emulator[i], snapshots_Emulator[i]))
    return (goodStatus & goodSelect & goodEmulator),select_ASIC

def checkSnapshots(compare=True, verbose=False, bx=4):
    """Manually take a snapshot in BX bx"""
    snapshots,status,select=i2cSnapshot(bx)
    
    if verbose:
        output=''
        for i in range(12):
            logger.info('  CH {:02n}: {:048x}'.format(i,snapshots[i]))

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

            badSnapshots=[]
            for i in range(12):
                if shiftedSnapshots[i] != (vote & (2**(int(192-shift[i]))-1)):
                    badSnapshots.append(i)

            if len(badSnapshots)==0:
                logger.info(f'After shifting to accomodate select values, all snapshots match: {vote:048x}')
            else:
                errors={i: hex(snapshots[i]) for i in badSnapshots}
                logger.error(f'Vote of snapshots is {hex(vote)}, errors in snapshots : {errors}')
            return False

def get_HDR_MM_CNTR(previous=None):
    """ Get hdr mm cntr """
    x=call_i2c(args_name='CH_ALIGNER_*_hdr_mm_cntr')
    counts=np.array([x['ASIC']['RO'][f'CH_ALIGNER_{i}INPUT_ALL']['hdr_mm_cntr'] for i in range(12)])
    if previous is None:
        return counts

    agreement = (counts==previous) & ~(counts==65535)
    if agreement.all():
        logger.info(f'Good hdr_mm_counters, not increasing: {counts}')
    else:
        increase=np.argwhere((counts>previous) | (counts==65535)).flatten()
        logger.error(f'Increase in channels {increase}: {counts-previous}')
        logger.error(f'          previous values {previous}')
        logger.error(f'          current values {counts}')
    return counts

def statusLogging(sleepTime=120, N=30, snapshot=False, tag=""):
    """ Log hdr mm cntrs"""
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

def eRxEnableTests(patterns=None, verbose=False):
    """
    Check that the ERX_ch_[0-11]_enable register does what is expected
    Loops through a number of patterns, hitting 
    """
    call_i2c(args_name="ERX_ch_*_enable",args_value="1")

    if not patterns is None:
        enablePatterns=patterns
    else:
        enablePatterns=[]
        enablePatterns.append(np.array([1,0,1,0,1,0,1,0,1,0,1,0]))
        #enablePatterns.append(np.array([1]*1 + [0]*11)) #pattern included in single/double patterns
        #enablePatterns.append(np.array([1]*2 + [0]*10)) #pattern included in single/double patterns
        enablePatterns.append(np.array([1]*3 + [0]*9))
        enablePatterns.append(np.array([1]*4 + [0]*8))
        enablePatterns.append(np.array([1]*5 + [0]*7))
        enablePatterns.append(np.array([1]*6 + [0]*6))
        enablePatterns.append(np.array([1]*7 + [0]*5))
        enablePatterns.append(np.array([1]*8 + [0]*4))
        enablePatterns.append(np.array([1]*9 + [0]*3))
        #enablePatterns.append(np.array([1]*10 + [0]*2)) #pattern included in single/double patterns
        #enablePatterns.append(np.array([1]*11 + [0]*1)) #pattern included in single/double patterns

        #all combinations of single or double eRx
        for i in range(12):
            for j in range(i,12):
                p=np.zeros(12,dtype=int)
                p[[i,j]]=1
                enablePatterns.append(p)

    def snapshotCheckofEnabled(enables):
        #set all by i and j to enabled
        call_i2c(args_name='ERX_ch_[0-11]_enable',args_value=','.join([str(x) for x in enables]))

        snapshots,status,select=i2cSnapshot()
        snapshotsHex=np.array([f'{s:048x}' for s in snapshots])
        match=np.array(snapshotsHex=='8ad3a74e9ad5ab56aad7af5eb90000000a0204081a040810')

        #check that enabled links have good pattern, and disabled don't
        enabledLinksGood=match[enables==1].all() # all enable links have good pattern
        disabledLinksGood= ~(match[enables==0]).any() # non of disabled have good pattern

        #check that disabled links are repeating the same 32 bits
        disERXlist = enables==0
        basePattern=(snapshots[disERXlist] & 4294967295)
        disabledLinksRepeating = np.all( [ ( (snapshots[disERXlist] >> n*32) & 4294967295 ) == basePattern for n in range(6) ])

        return enabledLinksGood and disabledLinksGood and disabledLinksRepeating, snapshotsHex

    passTest=True
    for enables in enablePatterns:
        goodEnables  = snapshotCheckofEnabled(enables)
        if verbose:
            print(f'{enables} {"PASS" if goodEnables[0] else "FAIL"}')
        if not goodEnables[0]:
            print(f'Problem with pattern {enables}')
            print(goodEnables[1])
            passTest=False

        goodDisables = snapshotCheckofEnabled(1-enables)
        if verbose:
            print(f'{1-enables} {"PASS" if goodDisables[0] else "FAIL"}')
        if not goodDisables[0]:
            print(f'Problem with pattern {1-enables}')
            print(goodDisables[1])
            passTest=False

    #turn all of them back on
    call_i2c(args_name="ERX_ch_*_enable",args_value="1")

    return passTest

def continuousSnapshotCheck(verbose=False, bx=4):
    """Manually take a snapshot in BX bx"""
    snapshots,status,select=i2cSnapshot(bx)
    

    """
    fc = FastCommands()
    lc = LinkCapture()
    tv = TestVectors()
    fc.configure_fc()
    lc.stop_continous_capture(["lc-input"])
    lc.configure_acquire(["lc-input"],mode="BX",nwords=511,total_length=511,bx=3560,verbose=False)
    lc.do_continous_capture(["lc-input"])
    """

    try:
        while True:
            snapshots,status,select=i2cSnapshot(bx)

            if len(np.unique(snapshots))==1:
                logger.info(f'All snapshots match : {hex(snapshots[0])}')
            else:
                """
                data = lc.get_captured_data(["lc-input"],511,False)
                datahex = tv.fixed_hex(data["lc-input"],8)
                for n in datahex: logger.info(','.join(n))
                """

                shift = select-select.min()
                shiftedSnapshots=(snapshots>>shift)

                vote=0
                for i in range(192):
                    vote += (((shiftedSnapshots>>i)&1).sum()>6)<<i

                badSnapshots=[]
                for i in range(12):
                    if shiftedSnapshots[i] != (vote & (2**(int(192-shift[i]))-1)):
                        badSnapshots.append(i)

                if len(badSnapshots)==0:
                    logger.info(f'After shifting to accomodate select values, all snapshots match: {hex(vote)}')
                else:
                    errors={i: hex(snapshots[i]) for i in badSnapshots}
                    logger.error(f'Vote of snapshots is {hex(vote)}, errors in snapshots : {errors.keys()}')
                    for k,v in errors.items():
                        logger.error(f'    eRx {k:02n} : {int(v,16):048x}')
    except KeyboardInterrupt:
        pass



if __name__=='__main__':
    """
    ERX monitoring
    - To change input test vectors
      python testing/eRx.py --tv --dtype --idir
    - To bypass output test vectors
      python testing/eRx.py --tv --idir IDIR --tv-name bypass --fname testOutput.csv
    - To log hdr mm cntrs over a period of time: 
      python testing/eRx.py --logging --sleep 120 -N 10
    - To take a snapshot manually at one bx
      python testing/eRx.py --snapshot --bx 4 
    - To check word alignment
      python testing/eRx.py --checkAlign --verbose
    - To align automatically and override alignment
      python testing/eRx.py --lrAlign --override
    - To get HDR MM CNTR
      python testing/eRx.py --hdrMM
    - To do PRBS scan
      python testing/eRx.py --prbs --sleep 1
    - For continuous snapshots
      python testing/eRx.py --contSnapshot
    """
    # ch = logging.StreamHandler()
    # ch.setLevel(logging.INFO)
    # logger.addHandler(ch)

    parser = argparse.ArgumentParser()
    parser.add_argument('--tv', dest='configureTV',default=False, action='store_true')
    parser.add_argument('--logging', dest='runLogging',default=False, action='store_true')
    parser.add_argument('--snapshot', dest='getSnapshot',default=False, action='store_true')
    parser.add_argument('--contSnapshot', dest='continuousSnapshots',default=False, action='store_true')
    parser.add_argument('--checkAlign', dest='checkWordAlignment',default=False, action='store_true')
    parser.add_argument('--lrAlign', dest='linkResetAlignment',default=False, action='store_true')
    parser.add_argument('--override', dest='override',default=False, action='store_true')
    parser.add_argument('--asic', dest='checkOnlyASIC',default=False, action='store_true')
    parser.add_argument('--hdrMM', dest='getHdrMM',default=False, action='store_true')
    parser.add_argument('--prbs', dest='prbsPhaseScan',default=False, action='store_true')
    parser.add_argument('--enableTest', dest='enableTests',default=False, action='store_true')

    parser.add_argument('-N',dest='N',default=1,type=int,help='Number of iterations to run')
    parser.add_argument('--sleep',dest='sleepTime',default=120,type=int,help='Time to wait between logging iterations')
    parser.add_argument('--tag',dest='tag',default="",type=str,help="Tag to save hdr mm cntr histogram")
    parser.add_argument('--threshold', dest='threshold',default=0,type=int, help='Threshold of number of allowed errors')
    parser.add_argument('--bx', dest='bx',default=4,type=int, help='BX to take snapshot in')
    parser.add_argument('--bcr', dest='bcr',default=0,type=int, help='BX to send BCR')
    parser.add_argument('--delay', dest='delay',default=None,type=int, help='Emulator delay setting for link alignment')
    parser.add_argument('--dtype', type=str, default="", help='dytpe (PRBS32,PRBS,PRBS28,debug,zeros)')
    parser.add_argument('--idir',dest="idir",type=str, default="", help='test vector directory')
    parser.add_argument('--fname',dest="fname",type=str, default="../testInput.csv", help='test vector filename')
    parser.add_argument('--tv-name', dest="tv_name", type=str, default="testvectors", help='test vector names')
    parser.add_argument('--select',dest="select", default=32, help="select value used to override in all input channels")
    
    parser.add_argument('--verbose', dest='verbose',default=False, action='store_true')

    args = parser.parse_args()

    if args.configureTV:
        from utils.test_vectors import TestVectors
        tv = TestVectors(args.tv_name)
        if args.tv_name=="bypass":
            tv.set_bypass(0)
        else:
            tv.set_bypass(1)
        tv.configure(args.dtype,args.idir,args.fname)

    elif args.runLogging:
        statusLogging(sleepTime=args.sleepTime, N=args.N, snapshot=args.getSnapshot, tag=args.tag)

    elif args.getSnapshot:
        checkSnapshots(verbose=True, bx=args.bx)

    elif args.checkWordAlignment:
        status,_=checkWordAlignment(verbose=args.verbose,ASIC_only=args.checkOnlyASIC)
        logger.info('Good Alignment' if status else 'Bad Alignment')

    elif args.override:
        select_ASIC = [args.select]*12
        overrideSelect(select_ASIC)
        
    elif args.linkResetAlignment:
        linkResetAlignment(snapshotBX=args.bx,orbsyncVal=args.bcr,override=args.override,verbose=args.verbose, delay=args.delay)

    elif args.getHdrMM:
        x=get_HDR_MM_CNTR()
        logger.info(f'hdr_mm_cntr '+" ".join(map(str,list(x))))

    elif args.prbsPhaseScan:
        from PRBS import scan_prbs
        args.i2c='ASIC'
        args.prbs=32
        err_counts, best_setting = scan_prbs(args,range(0,12),True)

    elif args.enableTests:
        eRxEnableTests(verbose=args.verbose)

    elif args.continuousSnapshots:
        continuousSnapshotCheck(verbose=args.verbose, bx=args.bx)
