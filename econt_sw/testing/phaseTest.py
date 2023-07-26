from set_econt import startup,set_phase,set_phase_of_enable,set_runbit,read_status,set_fpga,word_align,output_align,bypass_align,bypass_compare
from utils.asic_signals import ASICSignals
from i2c import I2C_Client
from PRBS import scan_prbs, repeat_scan
from PLL import scanCapSelect
from delay_scan import delay_scan
#from PowerSupplyControls import Agilent3648A
from time import sleep
from time import time

import csv
import argparse,os,pickle,pprint
import numpy as np
import sys,copy
import json

#i2cClient=I2C_Client(forceLocal=True)
nTrials = 1
#resets = ASICSignals()

def econt_qc(board,odir,voltage,voltageSetting,tickmark,tag=''):
    present = time()
    logging.info(f"QC TESTS")
    logging.info(f"Voltage: {voltage}, Output Directory: {odir}, Board: {board}.")

    # Initialize
    logging.info("Initialize with startup registers")
    startup()
    logging.info('\n')
   
    # Set FPGA to send PRBS
   # set_fpga()
   

    # PRBS phase scan
    logging.info(f"Scan phase w PRBS err counters")
    err_counts, best_setting = scan_prbs(32,'ASIC',0.05,tickmark,voltageSetting,range(0,12),True,verbose=False,odir=odir,tag=tag)
    logging.info(f"Best phase settings found to be {str(best_setting)}")
    logging.info('\n')

    # Scan IO delay scan                                                                                                                                                                                    
   # logging.info('From IO delay scan')
   # set_runbit(0)
   # i2cClient.call(args_yaml="configs/alignOutput_TS.yaml",args_i2c='ASIC,emulator',args_write=True)
   # set_runbit(1)
   # logging.debug(f"Configured ASIC/emulator with all eTx")
   # bit_counts, err_counts = delay_scan(odir,ioType='from',tag=tag)
   # new_array = []
   # new_array2 = []
   # for i in range(13):
   #     new_array.append(list(np.array(err_counts[i])/np.array(bit_counts[i])))
   # 
  #  with open(f'{odir}/{voltageSetting}_{tickmark}_delay_scan_errors.txt','w') as filehandle:
  #      json.dump(new_array, filehandle)
        
   # logging.debug("Error counts form IO delay scan: %s"%err_counts)
    #logging.info('\n')
   
   
   
    # Other init steps
   # set_phase(best_setting=','.join([str(i) for i in best_setting]))
   # set_phase_of_enable(0)
   # set_runbit(1)
   # read_status()
   
    # Test the different track modes and train channels   
#    logging.info('Testing track modes')
#    for trackmode in range(1, 4):
#        i2cClient.call(args_name='EPRXGRP_TOP_trackMode', args_value=f'{trackmode}')
#        phaseSelect_vals = []
#        for trainchannel in range(0, 50):
#            i2cClient.call(args_name='CH_EPRXGRP_*_trainChannel', args_value='1')
#            i2cClient.call(args_name='CH_EPRXGRP_*_trainChannel', args_value='0')
#            x = i2cClient.call(args_name='CH_EPRXGRP_*_status_phaseSelect',args_i2c='ASIC')
#            phaseSelect_vals.append([x['ASIC']['RO'][f'CH_EPRXGRP_{channel}INPUT_ALL']['status_phaseSelect'] for channel in range(0, 12)])
#
#        with open(f'{odir}/trackmode{trackmode}_phaseSelect_{board}board_voltage{voltageSetting}_{tickmark}.csv', 'w') as csvfile:
#            writer = csv.writer(csvfile)
#            writer.writerows(zip(*phaseSelect_vals))
   
    logging.info('\n')
    
    logging.info(f"Finalized test")
    elapsed = time() - present
    print(elapsed)
if __name__ == "__main__":
    """
    Test ECON-T functionality 
    """
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--board','-b', required=True, help='Board number')
    parser.add_argument('--odir', type=str, default='qc_results_08_22', help='output dir')
    parser.add_argument('--voltage', type=float, default=1.2, help='voltage')
    parser.add_argument('--tag', default=None, help='tag for extra logs')
    
    
    args = parser.parse_args()

    if args.tag is None:
        _tag=f'_{args.voltage}V_{args.board}board'
    else:
        _tag=f"_{args.voltage}V_{args.tag}_{args.board}board"

    os.system(f'mkdir -p {args.odir}')

    logName=f"{args.odir}/logFile{_tag}.log"
    voltage_str = f"Voltage {args.voltage}"
    import logging
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - {_voltage} - %(levelname)-6s %(message)s'.format(_voltage=voltage_str),
                        datefmt='%m-%d-%y %H:%M:%S',
                        filename=logName,
                        filemode='a')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    _f='%(asctime)s - {_voltage} - %(levelname)-6s %(message)s'.format(_voltage=voltage_str)
    console.setFormatter(logging.Formatter(_f))
    logging.getLogger().addHandler(console)
    repeat_scan(32,'ASIC',0.05,nTrials,"prbs_scan",range(0,12),True,verbose=False,odir=args.odir)
    delay_scan(args.odir,"test",ioType='from')  
    print(_tag)
#    econt_qc(args.board,args.odir,args.voltage,_tag)

## remember you added a couple new arguments to econt_qc such as count and set voltage
## tickmark is for when you run over the loop from 1 to 10
## setVoltage is the count that you have so that you can change the voltage setting on the board over the various test


#ps=Agilent3648A(host='192.168.1.50',addr=8)


#ps.SetLimits_1(v=1.2, i=0.6)
#resets.send_reset(reset='hard',i2c='ASIC')
#resets.send_reset(reset='hard',i2c='emulator')
#p,v,i=ps.ReadPower_1()
#logging.info(f'Power: {"On" if int(p) else "Off"}, Voltage: {float(v):.4f} V, Current: {float(i):.4f} A')

#for i in range (nTrials):
#    econt_qc(args.board,args.odir,args.voltage,120,i,tag=_tag)

#ps.SetLimits_1(v=1.08, i=0.6)
#resets.send_reset(reset='hard',i2c='ASIC')
#resets.send_reset(reset='hard',i2c='emulator')
#p,v,i=ps.ReadPower_1()
#logging.info(f'Power: {"On" if int(p) else "Off"}, Voltage: {float(v):.4f} V, Current: {float(i):.4f} A')
#do some stuff again

#for i in range (nTrials):
#    econt_qc(args.board,args.odir,args.voltage,108,i,tag=_tag)

#sleep(180)
#ps.SetLimits_1(v=1.2, i=0.6)
#now = time()
#sleep(9)
#resets.send_reset(reset='hard',i2c='ASIC')
#resets.send_reset(reset='hard',i2c='emulator')
#p,v,i=ps.ReadPower_1()
#print(f'Power: {"On" if int(p) else "Off"}, Voltage: {float(v):.4f} V, Current: {float(i):.4f} A')
##do some stuff again
#for i in range (nTrials):
   # later = 0
   # later = time() - now
   # if (later >= 300):
    #    econt_qc(args.board,args.odir,args.voltage,132,i,tag=_tag)
    #    p,v,i=ps.ReadPower_1()
    #    logging.info(f"Current = {float(i):.4f}")
    #    sleep(120)
   # else:
    #     econt_qc(args.board,args.odir,args.voltage,120,i,tag=_tag)
    #     p,v,i=ps.ReadPower_1()
    #     logging.info(f"Current = {float(i):.4f}")

#for i in range (nTrials):
#     econt_qc(args.board,args.odir,args.voltage,120,i,tag=_tag) 

