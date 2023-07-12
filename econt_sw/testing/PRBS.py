#!/usr/bin/python3
import os
import sys
sys.path.append( 'testing' )

from i2c import I2C_Client

import numpy as np
import csv
import time

import logging
logger = logging.getLogger("prbs")
logger.setLevel(logging.INFO)

from utils.test_vectors import TestVectors
tv = TestVectors(logLevelLogger=30)

i2cClient=I2C_Client(ip='localhost',forceLocal=True)

def clear_counters(args):
    """Clear MISC_rw counters"""
#    i2cClient.call(args_name=f'MISC_rw_ecc_err_clr',args_value='0',args_i2c=args.i2c)
    i2cClient.call(args_name=f'MISC_rw_ecc_err_clr',args_value='1',args_i2c=args.i2c)
    i2cClient.call(args_name=f'MISC_rw_ecc_err_clr',args_value='0',args_i2c=args.i2c)

def print_error_and_counters(args,channels,verbose=True):
    """Print error and counters"""
    outputs_aligner = i2cClient.call(args_name=f'CH_ALIGNER_*',args_i2c=args.i2c)[args.i2c]['RO']
    outputs_err = i2cClient.call(args_name=f'CH_ERR_*_raw_error_*',args_i2c=args.i2c)[args.i2c]['RO']

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
            logger.debug(f'{channel:02n}: {hdr_mm_err} {prbs_chk_err} {raw_error_prbs_chk_err} {orbsyn_hdr_err_cnt} {orbsyn_arr_err_cnt} {orbsyn_fc_err_cnt} {prbs_chk_err_cnt}')
        prbs_chk_err_cnts[channel] = prbs_chk_err_cnt

    return prbs_chk_err_cnts

def enable_prbschk(i2c='ASIC',prbs=32,channels=None,allch=True):
    """Enable prbs chck"""
    if allch:
        i2cClient.call(args_name=f'CH_ALIGNER_[0-11]_prbs_chk_en,CH_ALIGNER_[0-11]_prbs28_en',args_value='[0]*12,[0]*12',args_i2c=i2c)
        if prbs==28:
            i2cClient.call(args_name=f'CH_ALIGNER_[0-11]_prbs_chk_en,CH_ALIGNER_[0-11]_prbs28_en',args_value='1',args_i2c=i2c)
        else:
            i2cClient.call(args_name=f'CH_ALIGNER_[0-11]_prbs_chk_en',args_value='1',args_i2c=i2c)
    else:        
        for channel in channels:
            i2cClient.call(args_name=f'CH_ALIGNER_{channel}_prbs_chk_en',args_value='0',args_i2c=i2c)
            i2cClient.call(args_name=f'CH_ALIGNER_{channel}_prbs_chk_en',args_value='1',args_i2c=i2c)
            i2cClient.call(args_name=f'CH_ALIGNER_{channel}_prbs28_en',args_value='0',args_i2c=i2c)
            if prbs==28:
                i2cClient.call(args_name=f'CH_ALIGNER_{channel}_prbs28_en',args_value='1',args_i2c=i2c)

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
            i2cClient.call(args_name=f'CH_ALIGNER_{channel}_patt_en,CH_ALIGNER_{channel}_patt_sel',args_value='1,1',args_i2c=args.i2c)
            # 16 bit seed
            # i2cClient.call(args_name=f'CH_ALIGNER_{channel}_seed_in',args_value=f'{seed}',args_i2c=args.i2c) 
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

def scan_prbs(prbs,i2c,sleepTime,channels=range(12),allch=True,verbose=True,odir='./',tag=""):
    """Scan phaseSelect and read PRBS errors"""

    # reset things for PRBS
    i2cClient.call(args_yaml="configs/prbs.yaml",args_write=True,args_i2c=i2c)

    if prbs==28:
        tv.configure(dtype="PRBS28")
    else:
        # switch off the headers
        tv.configure(dtype="PRBS32")

    err_counts = []
    i2cClient.call(args_name='EPRXGRP_TOP_trackMode',args_value=f'0',args_i2c=i2c)

    enable_prbschk(i2c,prbs,channels,allch)
    for sel in range(0,15):
        # clear counters and hold
#        i2cClient.call(args_name=f'MISC_rw_ecc_err_clr',args_value='1',args_i2c=i2c)

        # change phaseSelect
        if allch:
            i2cClient.call(args_name='MISC_rw_ecc_err_clr,CH_EPRXGRP_[0-11]_phaseSelect',args_value=f'1,[{sel}]*12',args_i2c=i2c)
        else:
            command='MISC_rw_ecc_err_clr,'
            for channel in channels:
                command += f'CH_EPRXGRP_{channel}_phaseSelect,'
            command = command[:-1]
            i2cClient.call(args_name=command,args_value=f'1,[{sel}]*{len(channels)}',args_i2c=i2c)

        # enable prbs chk
#        enable_prbschk(i2c,prbs,channels,allch)
        # now count again
        i2cClient.call(args_name=f'MISC_rw_ecc_err_clr',args_value='0',args_i2c=i2c)
        # wait for a time
        time.sleep(sleepTime)

        # record counts
        outputs_aligner = i2cClient.call(args_name=f'CH_ALIGNER_[0-11]_prbs_chk_err_cnt',args_i2c=i2c)[i2c]['RO']
        prbs_chk_err_cnt = [outputs_aligner[f'CH_ALIGNER_{channel}INPUT_ALL']['prbs_chk_err_cnt'] for channel in range(12)]
        # prbs_chk_err_cnt = print_error_and_counters(args,channels,verbose=False)
        err_counts.append(prbs_chk_err_cnt)#list(prbs_chk_err_cnt.values()))

        if verbose:
            logger.info(' phaseSelect: {:02n}, prbs_chk_err_cnt: {}'.format(sel,str(err_counts[-1])))
            
    # disable prbs check
    if allch:
        i2cClient.call(args_name=f'CH_ALIGNER_[0-11]_prbs_chk_en',args_value='0',args_i2c=i2c)
    else:
        for channel in channels:
            i2cClient.call(args_name=f'CH_ALIGNER_{channel}_prbs_chk_en',args_value='0',args_i2c=i2c)

    err_counts = np.array(err_counts).astype(int)
    if verbose:
        logger.info(f'Error Array:\n{repr(err_counts)}')
    
    counts_window = []
    for i in range(15):
        # add counts over 3 setting window, summing i, i+1, and i-1 (mod 15)  
        counts_window.append( err_counts[i] + err_counts[(i-1)%15] + err_counts[(i+1)%15])

    if verbose:
        logger.debug('Error Counts over 3 setting window:')
        logger.debug(" ".join(map(str,range(len(counts_window))))+" \n")
        for c in counts_window:
            logger.debug(" ".join(map(str,c)))
        logger.debug('Minimum Arg:')
        logger.debug(" ".join(map(str,np.argmin(err_counts,axis=0))))

    tag = f"{sleepTime}s{tag}"
  #  with open(f"{odir}/{vSet}_{temp}_prbs_counters_scan_%s.csv"%tag, 'w') as f:
    #    writer = csv.writer(f, delimiter=',')
     #   writer.writerow([f'CH_{ch}' for ch in channels])
      #  for j in range(len(err_counts)):
       #     writer.writerow([int(err_counts[j][ch]) for ch in channels])




    with open(f"{odir}/prbs_counters_scan_%s.npy"%tag, 'wb') as \
f:
        np.save(f,err_counts)


    counts_window = np.array(counts_window)
    # print(counts_window)
    counts_window[ err_counts>0 ] += 255*3
    # print('thr ',counts_window)
    best_setting=np.array(counts_window).argmin(axis=0)
    if verbose:
        logger.info(f'Best phase settings: '+','.join(map(str,list(best_setting))))
        # logger.info(f'Best phase settings (!=0): '+','.join(map(str,list(np.array(counts_window[1:]).argmin(axis=0)))))

    y=(1*err_counts[:-4] + 3*err_counts[1:-3] + 5*err_counts[2:-2] + 3*err_counts[3:-1] + 1*err_counts[4:])

    y[ err_counts[2:-2]>0 ] += 2555
    x=y.argmin(axis=0)+2
    best_setting=x
    if verbose:
        logger.info(f'Best phase settings (5-setting window): '+','.join(map(str,list(x))))

    return err_counts, best_setting

def repeat_scan(prbs,i2c,sleepTime,n,file_name,channels=range(12),allch=True,verbose=True,odir='./',tag=""):
    tot_err_counts = []
    for i in range(n):
        err_counts, best_setting = scan_prbs(prbs,i2c,sleepTime,channels=range(12),allch=True,verbose=True,odir='./',tag="")
        tot_err_counts.append(err_counts)
    
    if n == 1:
        tot_err_counts = tot_err_counts[0]
    
    if file_name:
        with open(f"{odir}/{file_name}.npy","wb") as f:
            np.save(f, tot_err_counts)


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
    parser.add_argument('--sleep',dest='sleepTime',default=0.1,type=float,help='Time to wait between logging iterations')
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
        scan_prbs(args.prbs,args.i2c,args.sleepTime,channels,allch,verbose=True)
