#!/usr/bin/python3
from urllib.request import urlopen
import time
import sys
sys.path.append( 'testing' )
from i2c import call_i2c

import datetime
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--fname', default=f'i2c', help='i2c log name')
parser.add_argument('--snapshot', default=False, action='store_true', help='take snapshot after each read')
parser.add_argument('--debug', default=False, action='store_true', help='print local SC time to debug')
args = parser.parse_args()

import logging
#fname = f'{args.fname}_{datetime.datetime.now().strftime("%m_%d_%Y")}'
fname = f'{args.fname}'
logger = logging.getLogger("ITA")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
fh = logging.FileHandler(f'ITA_logs/{fname}.log')
fh.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s %(levelname)s  %(message)s")
ch.setFormatter(formatter)
fh.setFormatter(formatter)
logger.addHandler(ch)
logger.addHandler(fh)

URL='https://www-bd.fnal.gov/notifyservlet/www'

useLocal=True
localSCOffset=29

nsteps_SC=60.6

Pulse_SC_time=6


def RO_compare(previousStatus):
    if previousStatus is None: return

    i2c_RO_status=call_i2c(args_name='RO')
    diffs={}
    for chip in i2c_RO_status.keys():
        diffs_chip={}
        for block in i2c_RO_status[chip]['RO'].keys():
            diffs_block={}
            #SKIPS CH_ALIGNER AND CH_ERR RO comparisons for now, since we have word aligner issues
            if block.startswith('CH_ALIGNER_') and block.endswith('INPUT_ALL'): continue
            if block.startswith('CH_ERR_') and block.endswith('INPUT_ALL'): continue
            for reg,val in i2c_RO_status[chip]['RO'][block].items():
                if not previousStatus[block][reg]==val:
                    diffs_block[reg]=(previousStatus[block][reg],val)
            if not diffs_block=={}:
                diffs_chip[block]=diffs_block
        if not diffs_chip=={}:
            diffs[chip] = diffs_chip
    if diffs=={}:
        logger.info(f'RO Matches')
    else:
        logger.info('RO Mismatches: %s'%diffs)
        # import pprint
        # pprint.pprint(diffs)

def compare(previousStatus,regType='RW'):
    if previousStatus is None: return

    i2c_status=call_i2c(args_name=regType)
    diffs={}
    for chip in i2c_status.keys():
        diffs_chip={}
        for block in i2c_status[chip][regType].keys():
            diffs_block={}
            for reg,val in i2c_status[chip][regType][block].items():
                if not previousStatus[block][reg]==val:
                    diffs_block[reg]=(hex(previousStatus[block][reg]),hex(val))
            if not diffs_block=={}:
                diffs_chip[block]=diffs_block
        if not diffs_chip=={}:
            diffs[chip] = diffs_chip
    if diffs=={}:
        logger.info(f'{regType} Matches')
    else:
        logger.info(f'{regType} Mismatches: %s'%diffs)

prevROstatus=None
prevRWstatus=None

first=True
try:
    while True:
        if useLocal:
            _time=round((time.time()-localSCOffset)%nsteps_SC,1)
            if args.debug: logger.info(f'local SC time is {_time}')
        else:
            response = urlopen(URL).read()
            _time = float(str(response).split('SC time</a> = ')[1].split(' / ')[0])
#        if ((abs(_time-Pulse_SC_time)%nsteps_SC) < 1):
        if (abs(_time-Pulse_SC_time) < 1):
            logger.info(f'PULSE IS COMING:')
        elif (abs(_time-Pulse_SC_time)%nsteps_SC)>10 and (abs(_time-Pulse_SC_time)%nsteps_SC)<12:
            x = time.time()
            logger.info(f'CHECK I2C STATUS:')
            #rw_match = call_i2c(args_compare=True)
            compare(prevRWstatus,'RW')
            # if (rw_match['ASIC']=='keys: '):
            #     logger.info('RW Matches')
            # else:
            #     logger.info('RW Mismatches: %s'%rw_match)
            RO_compare(prevROstatus)
            logger.info(f'   Took {round(time.time()-x,2)} seconds')
            
            #take Snapshot
            if args.snapshot:
                call_i2c(args_name='ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,CH_ALIGNER_*_per_ch_align_en,ALIGNER_snapshot_arm',args_value='1,1,[0]*12,0')
                call_i2c(args_name='ALIGNER_snapshot_arm',args_value='1')
                snapshots=call_i2c(args_name='CH_ALIGNER_*_snapshot')['ASIC']['RO']

                for i in range(12):
                    x = hex(snapshots[f"CH_ALIGNER_{i}INPUT_ALL"]['snapshot'])
                    logger.info(f'     CH_ALIGNER_{i}_snapshot {x}')
                call_i2c(args_name='ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,CH_ALIGNER_*_per_ch_align_en,ALIGNER_snapshot_arm',args_value='0,1,[1]*12,0')

#        elif _time>30 and _time<32:
            #sleep two seconds before the write, rather than trying to time in both read and write separately
            time.sleep(2)
            x = time.time()
            logger.info(f'WRITE I2C DEFAULTS:')
            call_i2c(args_yaml='configs/updatedDefaults.yaml',args_write=True)
#            call_i2c(args_yaml='configs/ITA_init_align.yaml',args_write=True)

            #reset FCTRL error counter
            call_i2c(args_name='FCTRL_reset_b_fc_counters,MISC_rw_ecc_err_clr',args_value='0,1')
            call_i2c(args_name='FCTRL_reset_b_fc_counters,MISC_rw_ecc_err_clr',args_value='1,0')
#            print(call_i2c(args_name='FCTRL_*'))

            status=call_i2c(args_name='ALL')
            prevROstatus=status['ASIC']['RO']
            prevRWstatus=status['ASIC']['RW']
            if first:
                logger.info('Initial RO Status')
                logger.info('%s'%prevROstatus)
                logger.info('Initial RW Status')
                logger.info('%s'%prevRWstatus)
                first=False
#            prevRWstatus=call_i2c(args_name='RW')

            logger.info(f'   Took {round(time.time()-x,2)} seconds')
        time.sleep(1)

except KeyboardInterrupt:
    logging.info(f'Closing')

