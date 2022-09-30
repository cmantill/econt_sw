import sys
import os
sys.path.append( 'testing' )
from i2c import I2C_Client
from eRx import checkSnapshots
from eTx import capture
from PLL import scanCapSelect

import subprocess

from set_econt import startup,set_phase,set_phase_of_enable,set_runbit,read_status,word_align,output_align,simple_output_align,delay_scan

useGPIB=True

try:
    from emailLogin import GMAIL_USER,GMAIL_PASSWORD
except:
    GMAIL_USER=None
    GMAIL_PASSWORD=None

import smtplib
from email.message import EmailMessage

def sendEmail(SUBJECT,TEXT,RECIPIENT=['dnoonan08@gmail.com','criss.ms7@gmail.com','jhirsch@fnal.gov','james.f.hirschauer@gmail.com']):
    if GMAIL_USER is None or GMAIL_PASSWORD is None:
        print('No User')
        return

    # creates SMTP session
    s = smtplib.SMTP('smtp.gmail.com', 587)

    # start TLS for security
    s.starttls()

    # Authentication
    s.login(GMAIL_USER, GMAIL_PASSWORD)

    # message to be sent
    message = EmailMessage()
    message.set_content(TEXT)
    message['Subject']=SUBJECT
    message['From']=GMAIL_USER
    message['To']=RECIPIENT

    # sending the mail
    s.send_message(message)

    # terminating the session
    s.quit()


if useGPIB:
    sys.path.append( 'gpib' )
    from TestStand_Controls import psControl
#    gpib_ip='POOL05550020.cern.ch' #'128.141.89.226'
    ps=psControl(host='POOL05550020.cern.ch',timeout=3)
    try:
        ps.reconnect()
    except:
        print("Can't connect to power supply GPIB")
    rtd=psControl(host='POOL05550016.cern.ch',timeout=3)
    try:
        rtd.reconnect()
    except:
        print("Can't connect to RTD GPIB")

from utils.asic_signals import ASICSignals
from PRBS import scan_prbs

import argparse
from datetime import datetime
from time import sleep

from hexactrl_interface import hexactrl_interface
import pprint
import numpy as np


#### define try/except loops, in an attempt to solve timeout issue which killed script (final except will
def Read_Power(maxTries=5):
    _n=0
    while _n<maxTries:
        try:
            p,v,i=ps.Read_Power()
            break
        except:
            _n += 1
            p,v,i=-1,-1,-1
    if _n==maxTries:
        try:
            ps.reconnect()
        except:
            logging.error('Unable to reconnect to GPIB')
    return p,v,i

def readRTD(maxTries=5):
    _n=0
    while _n<maxTries:
        try:
            temperature,resistance=rtd.readRTD()
            break
        except:
            _n += 1
            temperature,resistance=-1,-1
    if _n==maxTries:
        try:
            rtd.reconnect()
        except:
            logging.error('Unable to reconnect to GPIB')
    return temperature,resistance

def SetVoltage(v,maxTries=5):
    _n=0
    while _n<maxTries:
        try:
            ps.SetVoltage(v)
            output=v
            break
        except:
            _n += 1
            output=-1
    if _n==maxTries:
        ps.reconnect()
    sleep(1)
    return output

board=9

suppressBlocks=[]#['CH_ALIGNER_','INPUT_ALL'],
#                ['CH_ERR_','INPUT_ALL']]

i2cClient=I2C_Client(ip='localhost',forceLocal=True)
resets=ASICSignals()
hexactrl=hexactrl_interface()

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
    return diffs

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

def CapSelAndPhaseScans(voltage,timestamp):
    goodVals=scanCapSelect(verbose=False,saveToFile=False)
    logging.info(f'Good PLL settings V={voltage:.2f}: {goodVals}')
    i2cClient.call('PLL_*CapSelect',args_value='27')

    v=f'{voltage:.2f}'.replace('.','_')
    _dir=f'phaseScans/board_{board}/voltage_{v}/{timestamp}'
    os.makedirs(_dir)
    settings = {}
    settings_trackMode1 = {}
    for i_capSel in goodVals:
        p,v,i=Read_Power()
        i2cClient.call('PLL_*CapSelect',args_value=f'{i_capSel}')
        pusm_state=i2cClient.call('PUSM_state')['ASIC']['RO']['MISC_ALL']['misc_ro_0_PUSM_state']
        logging.info(f'   CapSel={i_capSel}, V={voltage:.2f}, PUSM={pusm_state}, V={float(v):.2f}, I={float(i):.6f}')
        err,setting=scan_prbs(32,'ASIC',0.01,range(12),True,verbose=False)
        settings[i_capSel] = setting
        np.savetxt(f'{_dir}/eRx_PhaseScan_CapSelect_{i_capSel}.csv',err,'% 3s',delimiter=',')

        set_phase(trackMode=1)
        phaseSel=i2cClient.call(args_name='CH_EPRXGRP_[0-11]_status_phaseSelect',args_i2c='ASIC')['ASIC']['RO']
        settings_trackMode1[i_capSel]=[phaseSel[f'CH_EPRXGRP_{i}INPUT_ALL']['status_phaseSelect'] for i in range(12)]
        i2cClient.call(args_name='EPRXGRP_TOP_trackMode',args_value=f'0',args_i2c='ASIC')

        delay_errors=delay_scan(odir=None)
        delay_errors_array=np.array(list(delay_errors.values())).T
        np.savetxt(f'{_dir}/eTx_DelayScan_CapSelect_{i_capSel}.csv',delay_errors_array,'% 5s',delimiter=',')


    with open(f'{_dir}/phaseSelect_TrackMode0.txt','w') as _file:
        _file.write(pprint.pformat(settings))
    with open(f'{_dir}/phaseSelect_TrackMode1.txt','w') as _file:
        _file.write(pprint.pformat(settings_trackMode1))
    capSel=goodVals[int(len(goodVals)/3)]

    # forcedCapSel=27 if voltage==1.2 else 28
    # logging.info(f'NOTE: ! Using {forcedCapSel} instead of {capSel}')
    # capSel=forcedCapSel
    return capSel,settings[capSel]


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

        err,best_PhaseSetting=scan_prbs(32,'ASIC',0.01,range(12),True,verbose=True)
        set_phase(best_setting=','.join([str(i) for i in best_PhaseSetting]))

        hexactrl.testVectors(['dtype:PRBS28'])

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

    if level==-1:  #input align only
        word_align(None,None)

        selVals=i2cClient.call('CH_ALI*select')['ASIC']['RO']
        selValString=','.join([str(selVals[f'CH_ALIGNER_{i}INPUT_ALL']['select']) for i in range(12)])
        i2cClient.call('CH_ALIGNER_[0-11]_sel_override_en,CH_ALIGNER_[0-11]_sel_override_val',args_value='[1]*12,'+selValString)

def resetErrorCounts():
    i2cClient.call('CH_ERR*err_dat*')
    i2cClient.call('ALIGNER_snapshot_en',args_value='0')
    hexactrl.send_fc('link_reset_roct')
    i2cClient.call('ALIGNER_snapshot_en',args_value='1')
    i2cClient.call('ERRTOP_clr_on_read_top,MISC_rw_ecc_err_clr,FCTRL_reset_b_fc_counters',args_value='1,1,0')
    i2cClient.call('ERRTOP_clr_on_read_top,MISC_rw_ecc_err_clr,FCTRL_reset_b_fc_counters',args_value='0,0,1')
    

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
    logging.info(f'Using Board {board}')

    try:
        rtd.ConfigRTD()
        temperature,resistance=rtd.readRTD()
    except:
        temperature,resistance=-1,-1

    try:
        ps.ConfigReadCurrent()
        ps.SetVoltage(1.2)
        p,v,i=ps.Read_Power()
    except:
        p,v,i=-1,-1,-1

    logging.info(f'Power: {"On" if int(p) else "Off"}, Voltage: {float(v):.4f} V, Current: {float(i):.6f} A, Temp: {temperature:.4f} C, Res.: {resistance:.2f} Ohms')

    dateTimeObj=datetime.now()
    timestamp = dateTimeObj.strftime("%d%b_%H%M%S")
    if not args.tag=="":
        timestamp=f'{args.tag}_{timestamp}'

    hexactrl.testVectors(['dtype:PRBS28'])
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

    consecutiveResetCount=0
    consecutiveErrorCount=0
    badVoltageCount=0
    voltageEmailSent=False

    logging.info(f'Starting stream compare (CTRL-C to stop and do capture and I2C compare)')
    hexactrl.start_daq()
    doDAQcompare = True 

    try:
        i__=0
        while True:
            if useGPIB:
                p,v,i=Read_Power()
                temperature,resistance=readRTD()
            else:
                p,v,i,temperature,resistance=-1,-1,-1,-1,-1
            logging.info(f'Power: {"On" if int(p) else "Off"}, Voltage: {float(v):.4f} V, Current: {float(i):.6f} A, Temp: {temperature:.4f} C, Res.: {resistance:.2f} Ohms')
            # logging.info(f'Power: {"On" if int(p) else "Off"}, Voltage: {float(v):.4f} V, Current: {float(i):.4f} A')

            # #trigger email if bad voltage readings multiple times
            # if float(v)<1.14 or float(v)>1.26:
            #     badVoltageCount += 1
            # else:
            #     badVoltageCount = 0

            # if badVoltageCount==5 and not voltageEmailSent:
            #     logging.error("Voltage bad for multiple consecutive readings")
            #     message = f'ECON-T voltage at bad settings\n\n\nPower: {"On" if int(p) else "Off"}, Voltage: {float(v):.4f} V, Current: {float(i):.6f} A, Temp: {temperature:.4f} C, Res.: {resistance:.2f} Ohms\n\n\nLAST 100 LINES OF LOG\n\n\n'
            #     logTail = subprocess.Popen(['tail','-n','100',args.logName],stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.readlines()
            #     message += ''.join([x.decode('utf-8') for x in logTail])
            #     dateTimeObj=datetime.now()
            #     timestamp = dateTimeObj.strftime("%d%b_%H%M%S")
            #     subject=f"ECON VOLTAGE ERROR {timestamp}"
            #     sendEmail(subject, message)
            #     voltageEmailSent=True


            #if we are getting continuous errors, turn off DAQ comparisons
            if (consecutiveResetCount >= 1) and doDAQcompare:
                logging.error("TOO MANY FAILED RESET ATTEMPTS, STOPPING DAQ COMPARISON")

                doDAQcompare=False


            # #if we are getting continuous errors, turn off DAQ comparisons
            # if (consecutiveResetCount > 5) and doDAQcompare:
            #     logging.error("TOO MANY FAILED RESET ATTEMPTS, STOPPING DAQ COMPARISON")

            #     logTail = subprocess.Popen(['tail','-n','100',args.logName],stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.readlines()
            #     message = 'ECON-T had too many failed resets\n\n\nLAST 100 LINES OF LOG\n\n\n'
            #     message += ''.join([x.decode('utf-8') for x in logTail])
            #     dateTimeObj=datetime.now()
            #     timestamp = dateTimeObj.strftime("%d%b_%H%M%S")
            #     subject=f"ECON RESET ERROR {timestamp}"
            #     sendEmail(subject, message)

            #     doDAQcompare=False


            doI2CCompare = (i__%6)==0  #every minute
            doDAQcapture = (i__%60)==0 #every 10 minutes
            doPhaseScans_A = (i__%120)==0 #every 20 minutes, minutes 0-10 (1.2 V)
            doPhaseScans_B = (i__%120)==60 #every 20 minutes, minutes 10-15 (1.08 V)
            doPhaseScans_C = (i__%120)==90 #every 20 minutes, minutes 15-20 (1.32 V)
            resetLevel=-1
            par_en_error=False
            errCount=0


            if doDAQcompare:
                errCount=hexactrl.get_daq_counters()

                if errCount>0:
                    dateTimeObj=datetime.now()
                    timestamp = dateTimeObj.strftime("%d%b_%H%M%S")
                    err,data=hexactrl.stop_daq(frow=36,capture=True, timestamp=timestamp,odir='logs')
                    hexactrl.start_daq()

                if errCount>200000000:
                    consecutiveErrorCount += 1
                    logging.error(f'Errors in {consecutiveErrorCount} consecutive comparisons')
                else:
                    consecutiveErrorCount = 0

            if doI2CCompare:
                post_Reg_Status=i2cClient.call('ALL')
                RO_compare(last_Reg_Status['ASIC']['RO'], post_Reg_Status)    
                RW_compare(last_Reg_Status['ASIC']['RW'], post_Reg_Status)
                last_Reg_Status=post_Reg_Status.copy()
                if ((post_Reg_Status['ASIC']['RO']['PLL_ALL']['pll_read_bytes_4to3_parallel_enable_intrA']==1) or 
                    (post_Reg_Status['ASIC']['RO']['PLL_ALL']['pll_read_bytes_4to3_parallel_enable_intrB']==1) or
                    (post_Reg_Status['ASIC']['RO']['PLL_ALL']['pll_read_bytes_4to3_parallel_enable_intrC']==1)):

                    logging.error('Parallel Enable Intr Error Observed')
                    par_en_error=True

            if doDAQcapture:
                #### Force a link capture, dumping 10 BX to the screen
                dateTimeObj=datetime.now()
                timestamp = dateTimeObj.strftime("%d%b_%H%M%S")
                err,data=hexactrl.stop_daq(frow=36,capture=False, timestamp=timestamp,odir='logs')
                data = capture(['lc-ASIC','lc-emulator','lc-input'],
                               nwords=10, mode='L1A', bx=0, csv=False, phex=True, 
                               odir=None, fname=None, trigger=False,verbose=True)
                data_ASIC=data['lc-ASIC']
                data_em=data['lc-emulator']
                if not (data_ASIC==data_em).all():
                    logging.error('MISMATCH')
                hexactrl.configure(True,64,64,nlinks=13)
                hexactrl.start_daq()

            if doPhaseScans_A or doPhaseScans_B or doPhaseScans_C:
                dateTimeObj=datetime.now()
                timestamp = dateTimeObj.strftime("%d%b_%H%M%S")
                err,data=hexactrl.stop_daq(frow=36,capture=True, timestamp=timestamp,odir='logs')
                logging.info(f"Starting Power Scans ( timestamp {timestamp} )")

                hexactrl.testVectors(['dtype:PRBS32'])
                if doPhaseScans_B:
                    #######
                    ####### Phase Scans at 1.32V
                    #######
                    logging.info(f'Setting to 1.32 V')
                    _v=SetVoltage(1.32)
                    if _v==-1:
                        logging.error('Problem setting voltage')
                    p,v,i=Read_Power()
                    temperature,resistance=readRTD()
                    logging.info(f'Power: {"On" if int(p) else "Off"}, Voltage: {float(v):.4f} V, Current: {float(i):.6f} A, Temp: {temperature:.4f} C, Res.: {resistance:.2f} Ohms')
                    # logging.info(f'Power: {"On" if int(p) else "Off"}, Voltage: {float(v):.4f} V, Current: {float(i):.4f} A')
                    capSel,best_PhaseSetting = CapSelAndPhaseScans(voltage=1.32,timestamp=timestamp)
                    vSetting=1.08

                if doPhaseScans_C:
                    #######
                    ####### Phase Scans at 1.08V
                    #######
                    logging.info(f'Setting to 1.08 V')
                    _v=SetVoltage(1.08)
                    if _v==-1:
                        logging.error('Problem setting voltage')
                    p,v,i=Read_Power()
                    temperature,resistance=readRTD()
                    logging.info(f'Power: {"On" if int(p) else "Off"}, Voltage: {float(v):.4f} V, Current: {float(i):.6f} A, Temp: {temperature:.4f} C, Res.: {resistance:.2f} Ohms')
                    # logging.info(f'Power: {"On" if int(p) else "Off"}, Voltage: {float(v):.4f} V, Current: {float(i):.4f} A')
                    capSel,best_PhaseSetting = CapSelAndPhaseScans(voltage=1.08,timestamp=timestamp)
                    # bestPhase=','.join([str(i) for i in best_PhaseSetting])
                    # logging.info(f'Setting PLL VCO CapSelect to {capSel} at V=1.08 with phaseSelect settings of {bestPhase}')
                    # i2cClient.call('PLL_*CapSelect',args_value=f'{capSel}')
                    vSetting=1.08

                if doPhaseScans_A:
                    #######
                    ####### Phase Scans at 1.20V
                    #######
                    logging.info(f'Setting to 1.2 V')
                    if useGPIB:
                        _v=SetVoltage(1.2,maxTries=25)
                        if _v==-1:
                            logging.error('Problem setting voltage')
                        p,v,i=Read_Power()
                        temperature,resistance=readRTD()
                    else:
                        p,v,i,temperature,resistance=-1,-1,-1,-1,-1
                    logging.info(f'Power: {"On" if int(p) else "Off"}, Voltage: {float(v):.4f} V, Current: {float(i):.6f} A, Temp: {temperature:.4f} C, Res.: {resistance:.2f} Ohms')
                    # logging.info(f'Power: {"On" if int(p) else "Off"}, Voltage: {float(v):.4f} V, Current: {float(i):.4f} A')
                    capSel,best_PhaseSetting = CapSelAndPhaseScans(voltage=1.2,timestamp=timestamp)
                    vSetting=1.2

                bestPhase=','.join([str(i) for i in best_PhaseSetting])
                logging.info(f'Setting PLL VCO CapSelect to {capSel} at V={vSetting} with phaseSelect settings of {bestPhase}')
                i2cClient.call('PLL_*CapSelect',args_value=f'{capSel}')

                ### Set phaseSelect, do output alignment, and restart DAQ comparisons
                set_phase(best_setting=bestPhase)

                hexactrl.testVectors(['dtype:PRBS28'])
                
                resets.send_reset(reset='soft')

                ####input word alignmet
                configureASIC(level=-1)

                #simple_output_align()
                configureASIC(level=0)

#                i2cClient.call('*threshold*',args_value='50',args_i2c='ASIC,emulator')
#                resetErrorCounts()
                # data = capture(['lc-ASIC','lc-emulator','lc-input'],
                #                nwords=10, mode='L1A', bx=0, csv=False, phex=True, 
                #                odir=None, fname=None, trigger=False,verbose=True)

                # hexactrl.empty_fifo()
                # hexactrl.configure(True,64,64,nlinks=13)
                doDAQcompare=True

                hexactrl.start_daq()



            #######
            ####### RESET SEQUENCES
            #######
            if par_en_error:
                logging.warning("Observed error in parallel enable, performing soft reset")
                dateTimeObj=datetime.now()
                timestamp = dateTimeObj.strftime("%d%b_%H%M%S")
                err,data=hexactrl.stop_daq(frow=36,capture=False)
                configureASIC(level=2)
                hexactrl.start_daq()

            elif consecutiveErrorCount>=3:
                dateTimeObj=datetime.now()
                timestamp = dateTimeObj.strftime("%d%b_%H%M%S")
                logging.warning("Starting Reset Process")
                
                err,data=hexactrl.stop_daq(frow=36,capture=False)
                resetLevel=0
                badData=True

                if badData: #try output alignment first
                    logging.warning("    Step 1 - Realign Output")
                    configureASIC(level=0)
                    hexactrl.start_daq()
                    sleep(1)
                    err,data=hexactrl.stop_daq(frow=36,capture=False)
                    badData = err>100000

                    if badData: #try word alignment and output alignment
                        logging.warning("    Errors Persisted, Step 2 - Realign Input")
                        configureASIC(level=1)
                        hexactrl.start_daq()
                        sleep(1)
                        err,data=hexactrl.stop_daq(frow=36,capture=False)
                        badData = err>100000
                        if badData: #try soft reset
                            logging.warning("    Errors Persisted, Step 3 - Soft Reset")
                            configureASIC(level=2)
                            hexactrl.start_daq()
                            sleep(1)
                            err,data=hexactrl.stop_daq(frow=36,capture=False)
                            badData = err>100000
                            if badData: #try hard reset
                                logging.warning("    Errors Persisted, Step 4 - Hard Reset")
                                configureASIC(level=3)
                                hexactrl.start_daq()
                                sleep(1)
                                err,data=hexactrl.stop_daq(frow=36,capture=False)
                                badData = err>100000
                                if badData:
                                    logging.warning("    Errors Persisted after Hard Reset")
                                else:
                                    logging.warning("    Hard Reset Fixed Errors")
                            else:
                                logging.warning("    Soft Reset Fixed Errors")
                        else:
                            logging.warning("    Input Word Alignment Fixed Errors")
                    else:
                        logging.warning("    Output Alignment Fixed Errors")
                    


                #increment or reset consecutiveResetCount
                if badData:
                    consecutiveResetCount += 1
                else:
                    consecutiveResetCount = 0
                #reset consecutive error counter (to not immediately go to reset next iteration)
                consecutiveErrorCount = 0
                hexactrl.start_daq()

            i__ += 1
            sleep(10)
    except KeyboardInterrupt:
        logging.info(f'Stopping')
        #####test email messaging 
        # logTail = subprocess.Popen(['tail','-n','100',args.logName],stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.readlines()
        # message = 'THIS IS A TEST EMAIL (want to make sure the email in the tid script is working)\n'
        # message += 'ECON-T Test stopped\n\n\nLAST 100 LINES OF LOG\n\n\n'
        # message += ''.join([x.decode('utf-8') for x in logTail])
        # dateTimeObj=datetime.now()
        # timestamp = dateTimeObj.strftime("%d%b_%H%M%S")
        # subject=f"ECON ERROR {timestamp}"
        # sendEmail(subject,message)

    except:
        logging.exception('Stopping because of exception')

        logTail = subprocess.Popen(['tail','-n','100',args.logName],stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.readlines()
        message = 'ECON-T Test stopped\n\n\nLAST 100 LINES OF LOG\n\n\n'
        message += ''.join([x.decode('utf-8') for x in logTail])
        dateTimeObj=datetime.now()
        timestamp = dateTimeObj.strftime("%d%b_%H%M%S")
        subject=f"ECON ERROR {timestamp}"
        sendEmail(subject,message)


    err,data=hexactrl.stop_daq(frow=36,capture=False, timestamp=timestamp,odir='logs')
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

