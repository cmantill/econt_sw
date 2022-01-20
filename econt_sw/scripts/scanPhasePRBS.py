#!/usr/bin/python3  
import os
import sys
sys.path.append( 'testing' )
from i2c import call_i2c

import logging
logger = logging.getLogger("prbs")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--link', default=-1, type=int, help='link to scan')
    parser.add_argument('--prbs28', default=False, action='store_true', help='send 28 bit PRBS w headers')

    args = parser.parse_args()

    if args.link==-1:
        channels = range(0,12)
    else:
        channels = [args.link]

    if args.prbs28:
        os.system('python testing/uhal-align_on_tester.py --step test-data --dtype PRBS28')
    else:
        os.system('python testing/uhal-align_on_tester.py --step test-data --dtype PRBS')
        
    for channel in channels:
        counts = {}
        for sel in range(0,16):
            call_i2c(args_yaml="configs/prbs.yaml",args_write=True)
            call_i2c(args_name=f'MISC_rw_ecc_err_clr',args_value='0')
            call_i2c(args_name=f'MISC_rw_ecc_err_clr',args_value='1')
            call_i2c(args_name=f'MISC_rw_ecc_err_clr',args_value='0')
            call_i2c(args_name=f'CH_EPRXGRP_{channel}_phaseSelect',args_value=f'{sel}')
            call_i2c(args_name=f'CH_ALIGNER_{channel}_prbs_chk_en',args_value='0')
            call_i2c(args_name=f'CH_ALIGNER_{channel}_prbs_chk_en',args_value='1')
            if args.prbs28:
                 call_i2c(args_name=f'CH_ALIGNER_{channel}_prbs28_en',args_value='0')
                 call_i2c(args_name=f'CH_ALIGNER_{channel}_prbs28_en',args_value='1')

            outputs = call_i2c(args_name=f'CH_ALIGNER_{channel}_prbs_chk_err_cnt,CH_ERR_{channel}_raw_error_*')
            call_i2c(args_name=f'ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,CH_ALIGNER_{channel}_per_ch_align_en,ALIGNER_snapshot_arm',args_value='1,1,0,0')
            call_i2c(args_name='ALIGNER_snapshot_arm',args_value='1')
            snapshot=call_i2c(args_name=f'CH_ALIGNER_{channel}_snapshot')['ASIC']['RO']
            x = hex(snapshot[f"CH_ALIGNER_{channel}INPUT_ALL"]['snapshot'])
            logger.info(f'PhaseSelect {sel}     CH_ALIGNER_{channel}_snapshot {x}')
            call_i2c(args_name='ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,CH_ALIGNER_*_per_ch_align_en,ALIGNER_snapshot_arm',args_value='0,1,[1]*12,0')

            counts[sel] = [outputs['ASIC']['RO'][f'CH_ALIGNER_{channel}INPUT_ALL']['prbs_chk_err_cnt'],outputs['ASIC']['RO'][f'CH_ERR_{channel}INPUT_ALL']['raw_error_prbs_chk_err']]

            print(call_i2c(args_rw='RO',args_block='CH_ALIGNER_0INPUT_ALL',args_register='status',args_parameter='prbs_chk_err,orbsyn_fc_err,orbsyn_arr_err,orbsyn_hdr_err,align_seu_err,hdr_mm_err,snapshot_dv,pattern_match'))
            
        logger.info(f'link {channel} phaseSelect : [prbs_chk_err_cnt,raw_error_prbs_chk_err]')
        logger.info('%s'%counts)
