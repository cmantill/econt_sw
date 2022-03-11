#!/usr/bin/python3  
import os
import sys
sys.path.append( 'testing' )

from i2c import call_i2c

import numpy as np
import csv
import time

import logging
logger = logging.getLogger("prbs")
logger.setLevel(logging.INFO)
# ch = logging.StreamHandler()
# ch.setLevel(logging.INFO)
# logger.addHandler(ch)

from utils.test_vectors import TestVectors
tv = TestVectors()

def clear_counters(args):
    """Clear MISC_rw counters"""
#    call_i2c(args_name=f'MISC_rw_ecc_err_clr',args_value='0',args_i2c=args.i2c)
    call_i2c(args_name=f'MISC_rw_ecc_err_clr',args_value='1',args_i2c=args.i2c)
    call_i2c(args_name=f'MISC_rw_ecc_err_clr',args_value='0',args_i2c=args.i2c)

def print_error_and_counters(args,channels,verbose=True):
    """Print error and counters"""
    outputs_aligner = call_i2c(args_name=f'CH_ALIGNER_*',args_i2c=args.i2c)[args.i2c]['RO']
    outputs_err = call_i2c(args_name=f'CH_ERR_*_raw_error_*',args_i2c=args.i2c)[args.i2c]['RO']

    prbs_chk_err_cnts = {};
    for channel in channels:
        aligner = outputs_aligner[f'CH_ALIGNER_{channel}INPUT_ALL']
        error = outputs_err[f'CH_ERR_{channel}INPUT_ALL']
        prbs_chk_err_cnt = aligner['prbs_chk_err_cnt']
        orbsyn_fc_err_cnt = aligner['orbsyn_fc_err_cnt']
        orbsyn_arr_err_cnt = aligner['orbsyn_arr_err_cnt']
        orbsyn_hdr_err_cnt = aligner['orbsyn_hdr_err_cnt']
        hdr_mm_err = aligner['status_hdr_mm_err']
        prbs_chk_err = aligner['status_prbs_chk_err']
        raw_error_prbs_chk_err = error['raw_error_prbs_chk_err']
        if verbose:
            # logger.info(f'{channel}: {hdr_mm_err} {prbs_chk_err} {raw_error_prbs_chk_err}')
            # logger.info(f'{channel}: {orbsyn_hdr_err_cnt} {orbsyn_arr_err_cnt} {orbsyn_fc_err_cnt} {prbs_chk_err_cnt}')
            logger.info(f'{channel:02n}: {hdr_mm_err} {prbs_chk_err} {raw_error_prbs_chk_err} {orbsyn_hdr_err_cnt} {orbsyn_arr_err_cnt} {orbsyn_fc_err_cnt} {prbs_chk_err_cnt}')
        prbs_chk_err_cnts[channel] = prbs_chk_err_cnt

    return prbs_chk_err_cnts

def enable_prbschk(i2c='ASIC',prbs=32,channels=None,allch=True):
    """Enable prbs chck"""
    if allch:
        call_i2c(args_name=f'CH_ALIGNER_[0-11]_prbs_chk_en,CH_ALIGNER_[0-11]_prbs28_en',args_value='[0]*12,[0]*12',args_i2c=i2c)
        call_i2c(args_name=f'CH_ALIGNER_[0-11]_prbs_chk_en,CH_ALIGNER_[0-11]_prbs28_en',args_value=f'[1]*12,[{1 if prbs==28 else 0}]*12',args_i2c=i2c)
    else:
        for channel in channels:
            call_i2c(args_name=f'CH_ALIGNER_{channel}_prbs_chk_en',args_value='0',args_i2c=i2c)
            call_i2c(args_name=f'CH_ALIGNER_{channel}_prbs_chk_en',args_value='1',args_i2c=i2c)
            call_i2c(args_name=f'CH_ALIGNER_{channel}_prbs28_en',args_value='0',args_i2c=i2c)
            if prbs==28:
                call_i2c(args_name=f'CH_ALIGNER_{channel}_prbs28_en',args_value='1',args_i2c=i2c)

def check_prbs(args,channels,allch):
    """Check PRBS"""
    if args.fixed:
        # send a fixed pattern
        tv.configure(dtype="",idir="configs/test_vectors/counterPatternInTC_by2/RPT/")
    elif args.opposite:
        # send oppposite PRBS on purpose
        if args.prbs==28:
            tv.configure(dtype="PRBS32")
        else:
            tv.configure(dtype="PRBS28")
    elif args.internal:
        for channel in channels:
            call_i2c(args_name=f'CH_ALIGNER_{channel}_patt_en,CH_ALIGNER_{channel}_patt_sel',args_value='1,1',args_i2c=args.i2c)
            # 16 bit seed
            # call_i2c(args_name=f'CH_ALIGNER_{channel}_seed_in',args_value=f'{seed}',args_i2c=args.i2c) 
    else:
        if args.prbs==28:
            tv.configure(dtype="PRBS28")
        else:
            tv.configure(dtype="PRBS32")
    
    # clear counters
    clear_counters(args)

    # enable prbs chk
    enable_prbschk(args.i2c,args.prbs,channels,allch)
    logger.info('CHANNEL: hdr_mm_err prbs_chk_err raw_error_prbs_chk_err')
    logger.info('CHANNEL: orbsyn_hdr_err_cnt orbsyn_arr_err_cnt orbsyn_fc_err_cnt prbs_chk_err_cnt')
    
    # print counters
    print_error_and_counters(args,channels)

def scan_prbs(args,channels,allch,verbose=True):
    """Scan phaseSelect and read PRBS errors"""

    # reset things for PRBS
    call_i2c(args_yaml="configs/prbs.yaml",args_write=True,args_i2c=args.i2c)
    if args.prbs==28:
        tv.configure(dtype="PRBS28")
    else:
        # switch off the headers
        tv.configure(dtype="PRBS32")

    err_counts = []
    call_i2c(args_name='EPRXGRP_TOP_trackMode',args_value=f'0',args_i2c=args.i2c)
    for sel in range(0,16):
        # clear counters and hold
        call_i2c(args_name=f'MISC_rw_ecc_err_clr',args_value='1',args_i2c=args.i2c)

        # change phaseSelect
        logger.debug(f'PhaseSelect: {sel}')
        if allch:
            call_i2c(args_name='CH_EPRXGRP_[0-11]_phaseSelect',args_value=f'{sel}',args_i2c=args.i2c)
        else:
            for channel in channels:
                call_i2c(args_name=f'CH_EPRXGRP_{channel}_phaseSelect',args_value=f'{sel}',args_i2c=args.i2c)

        # enable prbs chk
        enable_prbschk(args.i2c,args.prbs,channels,allch)
        # now count again
        call_i2c(args_name=f'MISC_rw_ecc_err_clr',args_value='0',args_i2c=args.i2c)
        # wait for a time
        time.sleep(args.sleepTime)
        # disable prbs check
        if allch:
            call_i2c(args_name=f'CH_ALIGNER_[0-11]_prbs_chk_en',args_value='0',args_i2c=args.i2c)
        else:
            for channel in channels:
                call_i2c(args_name=f'CH_ALIGNER_{channel}_prbs_chk_en',args_value='0',args_i2c=args.i2c)
        # record counts
        outputs_aligner = call_i2c(args_name=f'CH_ALIGNER_[0-11]_prbs_chk_err_cnt',args_i2c=args.i2c)[args.i2c]['RO']
        prbs_chk_err_cnt = [outputs_aligner[f'CH_ALIGNER_{channel}INPUT_ALL']['prbs_chk_err_cnt'] for channel in range(12)]
        # prbs_chk_err_cnt = print_error_and_counters(args,channels,verbose=False)
        err_counts.append(prbs_chk_err_cnt)#list(prbs_chk_err_cnt.values()))
        
        logger.info(' phaseSelect: {:02n}, prbs_chk_err_cnt: {}'.format(sel,str(err_counts[-1])))

    err_counts = np.array(err_counts).astype(int)

    counts_window = []
    for i in range(15):
        # add counts over 3 setting window, summing i, i+1, and i-1 (mod 15)  
        counts_window.append( err_counts[i] + err_counts[(i-1)%15] + err_counts[(i+1)%15])

    if verbose:
        logger.info('Error Counts over 3 setting window:')
        logger.info(" ".join(map(str,range(len(counts_window))))+" \n")
        for c in counts_window:
            logger.info(" ".join(map(str,c)))
        logger.info('Minimum Arg:')
        logger.info(" ".join(map(str,np.argmin(err_counts,axis=0))))

    if verbose:
        with open("prbs_counters_scan_%is.csv"%args.sleepTime, 'w') as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerow([f'CH_{ch}' for ch in channels])
            for j in range(len(err_counts)):
                writer.writerow([int(err_counts[j][ch]) for ch in channels])

    counts_window = np.array(counts_window)
    # print(counts_window)
    counts_window[ err_counts[:-1]>0 ] += 255*3
    # print('thr ',counts_window)
    best_setting=np.array(counts_window).argmin(axis=0)
    if verbose:
        logger.info(f'Best phase settings: '+','.join(map(str,list(best_setting))))
        # logger.info(f'Best phase settings (!=0): '+','.join(map(str,list(np.array(counts_window[1:]).argmin(axis=0)))))

    return err_counts, best_setting

if __name__ == "__main__":
    """
    All things PRBS related
    - PRBS scan (at a given sleep time)
      python testing/PRBS.py --prbs 32 --sleep 10 --threshold 500
    - Check that internal PRBS check works (i.e. prbs_chk_err_cnt should not increase and prbs_chk_err should be 0)
      python testing/PRBS.py --prbs 28 --check
      python testing/PRBS.py --prbs 32 --check 
      - To send opposite PRBS: (e.g enable check for 32 PRBS but send 28 bit PRBS)
        python testing/PRBS.py --prbs 28 --check --opposite 
      - To check that we get PRBS error if we send fixed pattern:
        python testing/PRBS.py --prbs 28 --check --fixed
    """
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--link', default=-1, type=int, help='link to scan')
    parser.add_argument('--prbs', required=True, type=int, choices=[28,32], help='send 28/32 bit PRBS w headers')
    parser.add_argument('--i2c',  type=str, default='ASIC', help="keys of i2c addresses(ASIC,emulator)")
    parser.add_argument('--sleep',dest='sleepTime',default=120,type=int,help='Time to wait between logging iterations')
    parser.add_argument('--check', default=False, action='store_true', help='check that internal PRBS check works')
    parser.add_argument('--fixed', default=False, action='store_true', help='check that internal PRBS check gives error with fixed pattern')
    parser.add_argument('--opposite', default=False, action='store_true', help='check that internal PRBS check gives error with opposite PRBS')
    parser.add_argument('--internal', default=False, action='store_true', help='enable internal PRBS')
    parser.add_argument('--threshold', dest='threshold',default=500,type=int, help='Threshold of number of allowed errors ')
    args = parser.parse_args()

    if args.link==-1:
        allch = True
        channels = range(0,12)
    else:
        allch = False
        channels = [args.link]

    if args.check:
        check_prbs(args,channels,allch)
    else:
        scan_prbs(args,channels,allch)

