import sys
sys.path.append( 'testing' )
from i2c import I2C_Client
from eRx import checkSnapshots
from eTx import capture
from PLL import scanCapSelect

from set_econt import startup,set_phase,set_phase_of_enable,set_runbit,read_status,word_align,output_align,delay_scan

sys.path.append( 'gpib' )
from TestStand_Controls import psControl
ps=psControl('192.168.206.50')
ps.select(48)
ps.SetVoltage(None,1.2)
from utils.asic_signals import ASICSignals
from PRBS import scan_prbs

import argparse
from datetime import datetime
from time import sleep

from hexactrl_interface import hexactrl_interface
import pprint
import numpy as np

suppressBlocks=[]#['CH_ALIGNER_','INPUT_ALL'],
#                ['CH_ERR_','INPUT_ALL']]

i2cClient=I2C_Client(ip='localhost',forceLocal=True)
resets=ASICSignals()
hexactrl=hexactrl_interface()
hexactrl.testVectors(['dtype:PRBS28'])

def RO_compare(previousStatus, i2c_RO_status):
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

def RW_compare(previousStatus,i2c_status, fix=False):

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
            i2cClient.call(args_yaml='configs/ITA/temp.yaml',args_write=True)
        return yamlfix


#before a reset:
##  Take i2c snapshot
##  Capture data stream and save to log
##  Capture all i2c and save to log

### outputAlign
###  - checkErrorrs
### work_align
###  - checkErrors
### soft reset, word_align, output_align
###  - checkErrors
### hard rest, ...

#### DAQ error count every time
#### I2C compare every minute
#### every 10 minutes force link capture and save
#### every 20 minutes do phaseSelect scan, 1.08, 1.2, and 1.32 (output delay scan as well) 


def configureASIC(level=0):
    if level==3:
        resets.send_reset(reset='hard')

        startup()
        set_phase(board=10,trackMode=0)
        set_phase_of_enable(0)
        set_runbit()
        read_status()

    if level==2:
        resets.send_reset(reset='soft')

    if level>=1:
        word_align(None,None)
        ## 

        selVals=i2cClient.call('CH_ALI*select')['ASIC']['RO']
        selValString=','.join([str(selVals[f'CH_ALIGNER_{i}INPUT_ALL']['select']) for i in range(12)])
        i2cClient.call('CH_ALIGNER_[0-11]_sel_override_en,CH_ALIGNER_[0-11]_sel_override_val',args_value='[1]*12,'+selValString)

    if level>=0:
        output_align()
        i2cClient.call('*threshold*',args_value='50',args_i2c='ASIC,emulator')
        resetErrorCounts()

def resetErrorCounts():
    i2cClient.call('CH_ERR*err_dat*')
    i2cClient.call('ALIGNER_snapshot_en',args_value='0')
    hexactrl.send_fc('link_reset_roct')
    i2cClient.call('ALIGNER_snapshot_en',args_value='1')
    i2cClient.call('ERRTOP_clr_on_read_top,MISC_rw_ecc_err_clr',args_value='1')
    i2cClient.call('ERRTOP_clr_on_read_top,MISC_rw_ecc_err_clr',args_value='0')


### set threshold to 0 (or 50, or 100???)

if __name__=="__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--logName', default='logFile.log', help='log name')
    parser.add_argument('--tag', default="", help='extra information to add to the timestamp in daq comparisons')

    frequency=10 #seconds betwee runs

    args=parser.parse_args()

    import logging
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)-6s %(message)s',
                        datefmt='%m-%d-%y %H:%M:%S',
                        filename=args.logName,
                        filemode='a')

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)-6s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger().addHandler(console)

    logging.info(f'Starting')

    dateTimeObj=datetime.now()
    timestamp = dateTimeObj.strftime("%d%b_%H%M%S")
    if not args.tag=="":
        timestamp=f'{args.tag}_{timestamp}'

    logging.info('Configuring ASIC')
    configureASIC(level=3)

    initial_Reg_Status=i2cClient.call('ALL')
    last_Reg_Status=initial_Reg_Status.copy()
    with open(f'logs/Initial_I2C_{timestamp}.log','w') as _file:
        _file.write(pprint.pformat(initial_Reg_Status))



    data = capture(['lc-ASIC','lc-emulator','lc-input'],
                   nwords=10, mode='L1A', bx=0, csv=False, phex=True, 
                   odir=None, fname=None, trigger=False,verbose=True)
    data_ASIC=data['lc-ASIC']
    data_em=data['lc-emulator']
    if not (data_ASIC==data_em).all():
        logging.error('MISMATCH')

    logging.info(f'Configuring stream compare')
    hexactrl.empty_fifo()
    hexactrl.configure(True,64,64,nlinks=13)

    

    logging.info(f'Starting stream compare (CTRL-C to stop and do capture and I2C compare)')
    hexactrl.start_daq()

    try:
        i__=0
        while True:
            p,v,i=ps.Read_Power()
            logging.info(f'Power: {"On" if int(p) else "Off"}, Voltage: {float(v):.4f} V, Current: {float(i):.4f} A')

            a=hexactrl.get_daq_counters()

            if a>0:
                dateTimeObj=datetime.now()
                timestamp = dateTimeObj.strftime("%d%b_%H%M%S")
                err,data=hexactrl.stop_daq(frow=36,capture=True, timestamp=timestamp,odir='logs')
                hexactrl.start_daq()
            if (i__%6)==0:
                post_Reg_Status=i2cClient.call('ALL')
                RO_compare(last_Reg_Status['ASIC']['RO'], post_Reg_Status)    
                RW_compare(initial_Reg_Status['ASIC']['RW'], post_Reg_Status)
                last_Reg_Status=post_Reg_Status.copy()
            if (i__%60)==0:
                err,data=hexactrl.stop_daq(frow=36,capture=False, timestamp=timestamp,odir='logs')
                data = capture(['lc-ASIC','lc-emulator','lc-input'],
                               nwords=10, mode='L1A', bx=0, csv=False, phex=True, 
                               odir=None, fname=None, trigger=False,verbose=True)
                data_ASIC=data['lc-ASIC']
                data_em=data['lc-emulator']
                if not (data_ASIC==data_em).all():
                    logging.error('MISMATCH')
                hexactrl.start_daq()

            if (i__%120)==0:
                err,data=hexactrl.stop_daq(frow=36,capture=True, timestamp=timestamp,odir='logs')

                logging.info(f'Setting to 1.08 V')
                ps.SetVoltage(None,1.08)
                p,v,i=ps.Read_Power()
                logging.info(f'Power(1.08V): {"On" if int(p) else "Off"}, Voltage: {float(v):.4f} V, Current: {float(i):.4f} A')
                goodVals=scanCapSelect(verbose=False,saveToFile=False)
                logging.info(f'Good PLL settings: {goodVals}')
                i2cClient.call('PLL_*CapSelect',args_value='27')
                scan_prbs(32,'ASIC',0.1,range(12),True)
                delay_errors=delay_scan(odir=None)
                delay_errors_array=np.array(list(delay_errors.values())).T
                delay_errors_string=repr(delay_errors_array).replace(",\n       ",",").replace("],","],\n       ")
                logging.info(f'eTx delays errors\n{delay_errors_string}')

                logging.info(f'Setting to 1.32 V')
                ps.SetVoltage(None,1.32)
                p,v,i=ps.Read_Power()
                logging.info(f'Power(1.32V): {"On" if int(p) else "Off"}, Voltage: {float(v):.4f} V, Current: {float(i):.4f} A')
                goodVals=scanCapSelect(verbose=False,saveToFile=False)
                logging.info(f'Good PLL settings: {goodVals}')
                i2cClient.call('PLL_*CapSelect',args_value='27')
                scan_prbs(32,'ASIC',0.1,range(12),True)
                delay_errors=delay_scan(odir=None)
                delay_errors_array=np.array(list(delay_errors.values())).T
                delay_errors_string=repr(delay_errors_array).replace(",\n       ",",").replace("],","],\n       ")
                logging.info(f'eTx delays errors\n{delay_errors_string}')

                logging.info(f'Setting to 1.2 V')
                ps.SetVoltage(None,1.2)
                p,v,i=ps.Read_Power()
                logging.info(f'Power(1.2V): {"On" if int(p) else "Off"}, Voltage: {float(v):.4f} V, Current: {float(i):.4f} A')
                goodVals=scanCapSelect(verbose=False,saveToFile=False)
                logging.info(f'Good PLL settings: {goodVals}')
                i2cClient.call('PLL_*CapSelect',args_value='27')
                scan_prbs(32,'ASIC',0.1,range(12),True)
                delay_errors=delay_scan(odir=None)
                delay_errors_array=np.array(list(delay_errors.values())).T
                delay_errors_string=repr(delay_errors_array).replace(",\n       ",",").replace("],","],\n       ")
                logging.info(f'eTx delays errors\n{delay_errors_string}')
                
                set_phase(board=10,trackMode=0)
                hexactrl.testVectors(['dtype:PRBS28'])
                
                configureASIC(level=0)

                hexactrl.start_daq()
            i__ += 1
            sleep(10)
    except KeyboardInterrupt:
        logging.info(f'Stopping')
    
    err,data=hexactrl.stop_daq(frow=36,capture=True, timestamp=timestamp,odir='logs')
    if int(err)>0:
        print('ASIC')
        for x in data[:8]:
            print(','.join(list(x)))
        print('emulator')
        for x in data[8:16]:
            print(','.join(list(x)))
        diff=data[:8]==data[8:16]
        for x in diff:
            print(','.join([str(y) for y in x]))

    with open(f'logs/PostBeam_I2C_{timestamp}.log','w') as _file:
        _file.write(pprint.pformat(post_Reg_Status))

