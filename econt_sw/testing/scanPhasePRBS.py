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
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)

def clear_counters(args):
    call_i2c(args_name=f'MISC_rw_ecc_err_clr',args_value='0',args_i2c=args.i2c)
    call_i2c(args_name=f'MISC_rw_ecc_err_clr',args_value='1',args_i2c=args.i2c)
    call_i2c(args_name=f'MISC_rw_ecc_err_clr',args_value='0',args_i2c=args.i2c)

def print_error_and_counters(args,channels,verbose=True):
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
            logger.info(f'{channel}: {hdr_mm_err} {prbs_chk_err} {raw_error_prbs_chk_err}')
            logger.info(f'{channel}: {orbsyn_hdr_err_cnt} {orbsyn_arr_err_cnt} {orbsyn_fc_err_cnt} {prbs_chk_err_cnt}')
        prbs_chk_err_cnts[channel] = prbs_chk_err_cnt

    return prbs_chk_err_cnts

def enable_prbschk(args,channels):
    for channel in channels:
        call_i2c(args_name=f'CH_ALIGNER_{channel}_prbs_chk_en',args_value='0',args_i2c=args.i2c)
        call_i2c(args_name=f'CH_ALIGNER_{channel}_prbs_chk_en',args_value='1',args_i2c=args.i2c)
        if args.prbs==28:
            call_i2c(args_name=f'CH_ALIGNER_{channel}_prbs28_en',args_value='0',args_i2c=args.i2c)
            call_i2c(args_name=f'CH_ALIGNER_{channel}_prbs28_en',args_value='1',args_i2c=args.i2c)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--link', default=-1, type=int, help='link to scan')
    parser.add_argument('--prbs', required=True, type=int, choices=[28,32], help='send 28/32 bit PRBS w headers')
    parser.add_argument('--i2c',  type=str, default='ASIC', help="keys of i2c addresses(ASIC,emulator)")
    parser.add_argument('--check', default=False, action='store_true', help='check that internal PRBS check works')
    parser.add_argument('--fixed', default=False, action='store_true', help='check that internal PRBS check gives error with fixed pattern')
    parser.add_argument('--opposite', default=False, action='store_true', help='check that internal PRBS check gives error with opposite PRBS')
    parser.add_argument('--internal', default=False, action='store_true', help='enable internal PRBS')
    args = parser.parse_args()

    if args.link==-1:
        channels = range(0,12)
    else:
        channels = [args.link]

    if args.check:
        if args.fixed:
            # send fixed pattern
            os.system('python testing/uhal/align_on_tester.py --step test-data --idir configs/test_vectors/counterPatternInTC_by2/RPT/')
        elif args.opposite:
            # or send opposite PRBS on purpose
            if args.prbs==28:
                os.system('python testing/uhal/align_on_tester.py --step test-data --dtype PRBS')
            else:
                os.system('python testing/uhal/align_on_tester.py --step test-data --dtype PRBS28')
        else:
            if args.prbs==28:
                os.system('python testing/uhal/align_on_tester.py --step test-data --dtype PRBS28')
            else:
                os.system('python testing/uhal/align_on_tester.py --step test-data --dtype PRBS')

        # clear counters 
        clear_counters(args)

        # enable prbs chk
        enable_prbschk(args,channels)

        # orbsyn_cnt_max_val = 3563?
        logger.info('CHANNEL: hdr_mm_err prbs_chk_err raw_error_prbs_chk_err')
        logger.info('CHANNEL: orbsyn_hdr_err_cnt orbsyn_arr_err_cnt orbsyn_fc_err_cnt prbs_chk_err_cnt')
        print_error_and_counters(args,channels)

        exit(1)
    else:
        # reset things for PRBS
        call_i2c(args_yaml="configs/prbs.yaml",args_write=True,args_i2c=args.i2c)
        
        if args.internal:
            for channel in channels:
                call_i2c(args_name=f'CH_ALIGNER_{channel}_patt_en,CH_ALIGNER_{channel}_patt_sel',args_value='1,1',args_i2c=args.i2c)
                # set16 bit seed
                # call_i2c(args_name=f'CH_ALIGNER_{channel}_seed_in',args_value=f'{seed}',args_i2c=args.i2c)
        else:
            if args.prbs==28:
                os.system('python testing/uhal/align_on_tester.py --step test-data --dtype PRBS28')
            else:
                # switch off the headers in elinkOutputs 
                # in 32 bit PRB checking mode prbs_chk_err_cnt should not increment
                # while hdr_mm_cntr and orbsyn_hdr_err_cnt will increment
                # hdr_mm_cntr will increment 3563 times faster than orbsyn_hdr_err_cnt increments
                # but orbsyn_fc_err_cnt and orbsyn_arr_err_cnt should not increment.
                os.system('python testing/uhal/align_on_tester.py --step test-data --dtype PRBS32')

        selectvals = range(0,16)
        counts_per_sel = {}
        for sel in selectvals:
            # clear counters and hold
            call_i2c(args_name=f'MISC_rw_ecc_err_clr',args_value='1',args_i2c=args.i2c)
                
            print(f'Choosing phaseSelect to {sel}')
            for channel in channels:
                call_i2c(args_name=f'CH_EPRXGRP_{channel}_phaseSelect',args_value=f'{sel}',args_i2c=args.i2c)
        
            # now count again (swapped)
            #call_i2c(args_name=f'MISC_rw_ecc_err_clr',args_value='0',args_i2c=args.i2c)

            # enable prbs check
            enable_prbschk(args,channels)
        
            # now count again
            call_i2c(args_name=f'MISC_rw_ecc_err_clr',args_value='0',args_i2c=args.i2c)
            
            # wait for a time
            time.sleep(10)

            # disable prbs check
            for channel in channels:
                call_i2c(args_name=f'CH_ALIGNER_{channel}_prbs_chk_en',args_value='0',args_i2c=args.i2c)

            # record counters
            prbs_chk_err_cnt = print_error_and_counters(args,channels,verbose=False)
            counts_per_sel[sel] = prbs_chk_err_cnt

        counts_per_ch = {}
        mins_per_ch = {}
        for sel,cdict in counts_per_sel.items():
            for ch,err in cdict.items():
                if sel==0:
                    counts_per_ch[ch] = [err]
                else:
                    counts_per_ch[ch].append(err)
        for ch in counts_per_ch.keys():
            mins_per_ch[ch] = np.argsort(np.asarray(list(counts_per_ch[ch])))[0]
        # print(mins_per_ch)

        with open("prbs_counters_scan_10s.csv", 'w') as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerow([f'CH_{ch}' for ch in channels])
            for j in selectvals:
                writer.writerow([int(counts_per_sel[j][ch]) for ch in channels])
            writer.writerow(m for m in mins_per_ch.values())
            
        """
        # now check snapshot?
        call_i2c(args_name=f'ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,CH_ALIGNER_{channel}_per_ch_align_en,ALIGNER_snapshot_arm',args_value='1,1,0,0',args_i2c=args.i2c)
        call_i2c(args_name='ALIGNER_snapshot_arm',args_value='1',args_i2c=args.i2c)
        snapshot=call_i2c(args_name=f'CH_ALIGNER_{channel}_snapshot',args_i2c=args.i2c)[args.i2c]['RO']
        x = hex(snapshot[f"CH_ALIGNER_{channel}INPUT_ALL"]['snapshot'])
        logger.info(f'PhaseSelect {sel}     CH_ALIGNER_{channel}_snapshot {x}')
        call_i2c(args_name='ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,CH_ALIGNER_*_per_ch_align_en,ALIGNER_snapshot_arm',args_value='0,1,[1]*12,0',args_i2c=args.i2c)
        """