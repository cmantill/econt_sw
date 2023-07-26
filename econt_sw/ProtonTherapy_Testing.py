import sys
sys.path.append( 'testing' )
from i2c import I2C_Client
import argparse
from datetime import datetime
from time import sleep

from hexactrl_interface import hexactrl_interface
import pprint



i2cClient=I2C_Client(forceLocal=True)
suppressBlocks=[]#['CH_ALIGNER_','INPUT_ALL'],
#                ['CH_ERR_','INPUT_ALL']]

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

if __name__=="__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--logName', default='logFile.log', help='log name')
    parser.add_argument('--tag', default="", help='extra information to add to the timestamp in daq comparisons')
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
    initial_Reg_Status=i2cClient.call('ALL')
    dateTimeObj=datetime.now()
    timestamp = dateTimeObj.strftime("%d%b_%H%M%S")
    if not args.tag=="":
        timestamp=f'{args.tag}_{timestamp}'

    with open(f'logs/Initial_I2C_{timestamp}.log','w') as _file:
        _file.write(pprint.pformat(initial_Reg_Status))

    logging.info(f'Configuring stream compare')
    hexactrl=hexactrl_interface()
    hexactrl.empty_fifo()
    hexactrl.configure(True,64,64,nlinks=13)

    logging.info(f'Starting stream compare (CTRL-C to stop and do capture and I2C compare)')
    hexactrl.start_daq()
    counter = 0
    try:
        while True:
            a=hexactrl.get_daq_counters()
            sleep(1)
            counter+=1
            if (counter%10 == 0): 
                var = (i2cClient.call('PLL_parallel_enable_intrA,PLL_parallel_enable_intrB,PLL_parallel_enable_intrC'))
                A = var['ASIC']['RO']['PLL_ALL']['pll_read_bytes_4to3_parallel_enable_intrA']
                B = var['ASIC']['RO']['PLL_ALL']['pll_read_bytes_4to3_parallel_enable_intrB']
                C = var['ASIC']['RO']['PLL_ALL']['pll_read_bytes_4to3_parallel_enable_intrC']
                if ( A != 0 or B!= 0 or C != 0):
                       logging.info(f"PLL Parallel Enable Registers: {var['ASIC']['RO']['PLL_ALL']}")


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

    post_Reg_Status=i2cClient.call('ALL')
    RO_compare(initial_Reg_Status['ASIC']['RO'], post_Reg_Status)    
    RW_compare(initial_Reg_Status['ASIC']['RW'], post_Reg_Status)    
    with open(f'logs/PostBeam_I2C_{timestamp}.log','w') as _file:
        _file.write(pprint.pformat(post_Reg_Status))

