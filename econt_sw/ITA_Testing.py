#!/usr/bin/python3
from urllib.request import urlopen
import time
import sys
sys.path.append( 'testing' )
from i2c import call_i2c 

from datetime import datetime
import argparse

import zmq
import yaml

from zmq_controller import daqController

URL='https://www-bd.fnal.gov/notifyservlet/www'
Pulse_SC_time=6

def getOffset():
    offset=0
    response = urlopen(URL).read()
    _scTime,nsteps_SC=str(response).split('SC time</a> = ')[1].split(' </td>')[0].split(' / ')
    _scTime,nsteps_SC=float(_scTime), float(nsteps_SC)
    _time=round((time.time()-offset)%nsteps_SC,1)
    offset=round((_time-_scTime)%nsteps_SC,1)
    return _scTime, nsteps_SC, offset


suppressBlocks=[['CH_ALIGNER_','INPUT_ALL'],
                ['CH_ERR_','INPUT_ALL']]

def RO_compare(previousStatus):
    if previousStatus is None: return

    i2c_RO_status=call_i2c(args_name='RO', args_ip='192.168.1.48')
    diffs={}
    full_diffs={}
    for chip in i2c_RO_status.keys():
        diffs_chip={}
        full_diffs_chip={}
        for block in i2c_RO_status[chip]['RO'].keys():
            diffs_block={}
            debugOnly=False
            #SKIPS CH_ALIGNER AND CH_ERR RO comparisons for now, since we have word aligner issues
            for bName in suppressBlocks:
                if block.startswith(bName[0]) and block.endswith(bName[1]):
                    debugOnly=True
            for reg,val in i2c_RO_status[chip]['RO'][block].items():
                if not previousStatus[block][reg]==val:
                    diffs_block[reg]=(previousStatus[block][reg],val)
            if not diffs_block=={}:
                if debugOnly:
                    full_diffs_chip[block]=diffs_block
                else:
                    diffs_chip[block]=diffs_block
        if not diffs_chip=={}:
            diffs[chip] = diffs_chip
            full_diffs[chip] = full_diffs_chip
    if diffs=={} and full_diffs=={}:
        logging.info(f'RO Matches')
    elif diffs=={}:
        logging.error(f'RO Matches (some errors in suppressed blocks)')
        logging.debug(f'Suppressed RO Mismatches: %s'%full_diffs)
    else:
        logging.error('RO Mismatches: %s'%diffs)
        logging.debug('RO Mismatches: %s'%full_diffs)

def RW_compare(previousStatus,fix=False):
    if previousStatus is None: return

    i2c_status=call_i2c(args_name='RW', args_ip='192.168.1.48')
    yamlfix={'ECON-T':{'RW':{}}}

    diffs_chip={}
    for block in i2c_status['ASIC']['RW'].keys():
        diffs_block={}
        for reg,val in i2c_status['ASIC']['RW'][block].items():
            if not previousStatus[block][reg]==val:
                diffs_block[reg]=(hex(previousStatus[block][reg]),hex(val))
                if block in yamlfix['ECON-T']['RW']:
                    yamlfix['ECON-T']['RW'][block]['registers'][reg]={'value':previousStatus[block][reg]}
                else:
                    yamlfix['ECON-T']['RW'][block]={'registers':{reg:{'value':previousStatus[block][reg]}}}
        if not diffs_block=={}:
            diffs_chip[block]=diffs_block

    if diffs_chip=={}:
        logging.info('RW Matches')
        return True
    else:
        logging.error('RW Mismatches: %s'%diffs_chip)

        if fix:
            with open('configs/ITA/temp.yaml','w') as _f: 
                yaml.dump(yamlfix,_f)
            call_i2c(args_yaml='configs/ITA/temp.yaml',args_write=True)
        return yamlfix

def init_i2c_config(yaml_config=None):
    call_i2c(args_yaml='configs/ITA/ITA_defaults.yaml',args_write=True, args_ip='192.168.1.48',args_i2c='ASIC,emulator')
    if not yaml_config is None:
        if os.path.exists(yaml_config):
            call_i2c(args_yaml=yaml_config, args_write=True,args_ip='192.168.1.48',args_i2c='ASIC,emulator')
        else:
            logger.error(f'Yaml file {yaml_config} does not exist')
    rw_status=call_i2c(args_name='RW', args_ip='192.168.1.48')['ASIC']['RW']
    ro_status=call_i2c(args_name='RO', args_ip='192.168.1.48')['ASIC']['RO']

    logging.debug('Initial RO Status')
    logging.debug('%s'%ro_status)
    logging.debug('Initial RW Status')
    logging.debug('%s'%rw_status)

    return rw_status, ro_status


def main(yaml_config=None, snapshot=False, testVector=None, tag=""):

    uhalClient=daqController('192.168.1.48','6677')

    logging.debug('Starting uhal config')
    try:
        uhalClient.configure()
    except zmq.error.Again:
        logging.error("Timeout, check that uhal zmq_server is running")
        uhalClient.close()
        exit(1)
    except:
        logging.error("Unknown exception, exiting")
        exit(1)
        
    #configure test vector if supplied
    if not testVector is None:
        logging.debug('Configuring test vector')
        if testVector.endswith('.csv'):
            logging.info(f'Configuring inputs with test vectors from csv file: {testVector}')
            uhalClient.set_testVectors(f'fname:{testVector}')
        elif testVector in ['PRBS','PRBS28','PRBS32']:
            logging.info(f'Configuring inputs for {testVector}')
            uhalClient.set_testVectors(f'dtype:{testVector}')
        else:
            logging.error(f"Unknown testVector specified {testVector}")
            exit(1)
    
    init_RW_status, prev_RO_status=init_i2c_config(yaml_config)
    _time, nsteps_SC, localSCOffset=0,0,0

    dataStarted=False
    waiting_for_pulse=False
    dataFinished=True
    i2c_check_done=True
    snapshotTaken=True
    oot_dataStarted=True
    oot_dataFinished=True
    manualPLLUnlocked=True
    RO_status_captured=True
    done=True

    doPRBScheck=False

    previousLoLCount=-1

    i=0
    try:
        while True:
            if (i%100)==0:
                logging.debug(f'Resync Time:')
                logging.debug(f'Old: {_time}, {nsteps_SC}, {localSCOffset}')
                _time, nsteps_SC, localSCOffset=getOffset()
                i = 1
                logging.debug(f'New: {_time}, {nsteps_SC}, {localSCOffset}')
            else:
                _time=round((time.time()-localSCOffset)%nsteps_SC,1)
                i += 1


            # logging.info(f'{_time} / {nsteps_SC}')

            if (_time > (Pulse_SC_time - 5)%nsteps_SC) and _time<Pulse_SC_time and not dataStarted:
                logging.debug(f'Starting data comparisons')
                uhalClient.start_daq()
                dataStarted=True
                waiting_for_pulse=True

            elif (_time > Pulse_SC_time) and waiting_for_pulse:
                logging.info(f'PULSE IS COMING:')
                waiting_for_pulse=False
                dataStarted=False
                dataFinished=False
                i2c_check_done=False
                snapshotTaken=False
                oot_dataStarted=False
                oot_dataFinished=False
                manualPLLUnlocked=False
                RO_status_captured=False
                done=False

                doPRBScheck = not doPRBScheck

            elif (_time > (Pulse_SC_time+5)%nsteps_SC) and (abs(_time-Pulse_SC_time)%nsteps_SC)<10 and not dataFinished:
                logging.debug(f'Stopping comparisons:')
                dateTimeObj=datetime.now()
                timestamp = tag + dateTimeObj.strftime("%d%b_%H%M%S")
                uhalClient.stop_daq(timestamp)
                dataFinished=True

            elif (_time > (Pulse_SC_time+10)%nsteps_SC) and not i2c_check_done:
                x = time.time()
                logging.debug(f'CHECK I2C STATUS:')

                #reset PLL_LOCK_B counter on fpga
                pll_lock_b_count=int(uhalClient.getpll())
                if pll_lock_b_count>0:
                    logging.error('Increase in PLL_LOCK_B count from FPGA: %s'%pll_lock_b_count)
                uhalClient.resetpll()

                diffs=RW_compare(init_RW_status, fix=True)
                RO_compare(prev_RO_status)
                logging.debug(f'   Took {round(time.time()-x,2)} seconds')
                i2c_check_done=True

            elif (_time > (Pulse_SC_time+20)%nsteps_SC) and not snapshotTaken and snapshot:
                logging.debug(f'Taking snapshot')
                #take Snapshot
                call_i2c(args_name='ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,CH_ALIGNER_*_per_ch_align_en,ALIGNER_snapshot_arm',args_value='1,1,[0]*12,0', args_ip='192.168.1.48')
                call_i2c(args_name='ALIGNER_snapshot_arm',args_value='1', args_ip='192.168.1.48')
                snapshots=call_i2c(args_name='CH_ALIGNER_*_snapshot', args_ip='192.168.1.48')['ASIC']['RO']

                for i in range(12):
                    x = hex(snapshots[f"CH_ALIGNER_{i}INPUT_ALL"]['snapshot'])
                    logging.debug(f'     CH_ALIGNER_{i}_snapshot {x}')
                call_i2c(args_name='ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_arm',args_value='0,0', args_ip='192.168.1.48')
                snapshotTaken=True

            elif (_time > (Pulse_SC_time+25)%nsteps_SC) and not oot_dataStarted:
                logging.debug(f'Starting OOT data comparisons')
                uhalClient.start_daq()
                oot_dataStarted=True

            elif (_time > (Pulse_SC_time+35)%nsteps_SC) and not oot_dataFinished:
                logging.debug(f'Stopping OOT data taking')
                dateTimeObj=datetime.now()
                timestamp = tag + "OOT_" + dateTimeObj.strftime("%d%b_%H%M%S")
                uhalClient.stop_daq(timestamp)
                oot_dataFinished=True

            elif (_time > (Pulse_SC_time+36)%nsteps_SC) and not manualPLLUnlocked:
                ### Unlocking PLL, then relocking twice, to get increase in lfLossOfLockCount
                logging.debug(f'Unlocking PLL to increment Loss of Lock counter')
                newLoLCount=call_i2c(args_name='PLL_lfLossOfLockCount', args_ip='192.168.1.48')['ASIC']['RO']['PLL_ALL']['pll_read_bytes_2to0_lfLossOfLockCount']
                if (previousLoLCount>-1) and newLoLCount!=previousLoLCount:
                    logging.error(f'CHANGE IN PLL LossOfLockCount!!!! {previousLoLCount} to {newLoLCount}')

                prevCapSelectVal=call_i2c(args_name='PLL_CBOvcoCapSelect', args_ip='192.168.1.48')['ASIC']['RW']['PLL_ALL']['pll_bytes_17to13_fromMemToLJCDR_CBOvcoCapSelect']
                call_i2c(args_name='PLL_CBOvcoCapSelect',args_value='0', args_ip='192.168.1.48')
                call_i2c(args_name='PLL_CBOvcoCapSelect',args_value=f'{prevCapSelectVal}', args_ip='192.168.1.48')
                call_i2c(args_name='PLL_CBOvcoCapSelect',args_value='0', args_ip='192.168.1.48')
                call_i2c(args_name='PLL_CBOvcoCapSelect',args_value=f'{prevCapSelectVal}', args_ip='192.168.1.48')
                previousLoLCount=call_i2c(args_name='PLL_lfLossOfLockCount', args_ip='192.168.1.48')['ASIC']['RO']['PLL_ALL']['pll_read_bytes_2to0_lfLossOfLockCount']

                manualPLLUnlocked=True

            elif (_time > (Pulse_SC_time+40)%nsteps_SC) and not RO_status_captured:
                logging.debug(f'Capturing RO statuses')
                #reset FCTRL error counter
                call_i2c(args_name='FCTRL_reset_b_fc_counters,MISC_rw_ecc_err_clr',args_value='0,1', args_ip='192.168.1.48')
                call_i2c(args_name='FCTRL_reset_b_fc_counters,MISC_rw_ecc_err_clr',args_value='1,0', args_ip='192.168.1.48')

                #reset PLL_LOCK_B counter on fpga
                pll_lock_b_count=int(uhalClient.getpll())
                if pll_lock_b_count>0:
                    logging.error('Increase in PLL_LOCK_B count from FPGA (OUT OF TIME FROM BEAM): %s'%pll_lock_b_count)
                uhalClient.resetpll()

                x = time.time()
                prev_RO_status=call_i2c(args_name='RO', args_ip='192.168.1.48')['ASIC']['RO']
                logging.debug(f'   Took {round(time.time()-x,2)} seconds')
                RO_status_captured=True

            elif not done and RO_status_captured:
                logging.debug(f'Finished: {round(nsteps_SC-_time+Pulse_SC_time,1)} until pulse')
                done=True

            time.sleep(1)

    except KeyboardInterrupt:
        logging.info(f'Closing')


if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--logName', default='logFile.log', help='log name')
    parser.add_argument('--yaml', default=None, help='Name of yaml file to load')
    parser.add_argument('--testVector', default=None, help='type of test vector to send (csv file, or command such as PRBS, PRBS28, etc)')
    parser.add_argument('--tag', default="", help='extra information to add to the timestamp in daq comparisons')
    parser.add_argument('--snapshot', default=False, action='store_true', help='take snapshot after each read')

    parser.add_argument('--debug', default=False, action='store_true', help='print local SC time to debug')
    args = parser.parse_args()

    import logging
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)-6s %(message)s',
                        datefmt='%m-%d-%y %H:%M:%S',
                        filename=args.logName,
                        filemode='a')
    
    console = logging.StreamHandler()
    if args.debug:
        console.setLevel(logging.DEBUG)
    else:
        console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)-6s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger().addHandler(console)

    main(yaml_config=args.yaml, snapshot=args.snapshot, testVector=args.testVector)
    print('HERE2')
