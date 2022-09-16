from i2c import I2C_Client
import numpy as np
from time import sleep
import csv

import logging
logger = logging.getLogger("pll")
logger.setLevel(logging.INFO)

from utils.pll_lock_count import PLLLockCount

pll=PLLLockCount()
i2cClient = I2C_Client()

allowedCapSelectVals=np.array([  0,   1,   2,   3,   4,   5,   6,   7,   8,   9,  10,  11,  12,
                                 13,  14,  15,  24,  25,  26,  27,  28,  29,  30,  31,  56,  57,
                                 58,  59,  60,  61,  62,  63, 120, 121, 122, 123, 124, 125, 126,
                                 127, 248, 249, 250, 251, 252, 253, 254, 255, 504, 505, 506, 507,
                                 508, 509, 510, 511])

def scanCapSelect(verbose=False, odir='./', tag='', saveToFile=True):
    goodVals=[]
    vals_pusm = {}
    for i in allowedCapSelectVals:
        i2cClient.call('PLL_*CapSelect',args_value=str(i))
        sleep(0.2)
        status = i2cClient.call(args_name='PLL_lfLocked,PUSM_state')
        pusm_state = status['ASIC']['RO']['MISC_ALL']['misc_ro_0_PUSM_state']
        pll_locked = status['ASIC']['RO']['PLL_ALL']['pll_read_bytes_2to0_lfLocked']
        if verbose:
            logger.info(f'{i:03d} {i:09b} {pusm_state} {pll_locked}{" <<<" if pusm_state==9 else ""}')

        if pusm_state==9:
            goodVals.append(i)

        
        vals_pusm[i] = pusm_state
             
    if saveToFile:
        with open(f'{odir}/pll_capSelect_scan{tag}.csv', 'w') as csvfile:
            for key in vals_pusm.keys():
                csvfile.write("%s,%s\n"%(key,vals_pusm[key]))

    return goodVals

def get_count():
    logger.info('Loss of lock count %s'%pll.getCount())
    logger.info('Edge to count %s'%pll.edgeSel(read=True))
    pll.edgeSel(val=1)
    logger.info('Edge to count %s'%pll.edgeSel(read=True))
    pll.edgeSel(val=0)
    logger.info('Edge to count %s'%pll.edgeSel(read=True))
    logger.info('Loss of lock count %s'%pll.getCount())
    
    # reset counters
    pll.reset()
    
    logger.info('Loss of lock count %s'%pll.getCount())

if __name__=='__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s')
    # get_count()
    goodVals=scanCapSelect(verbose=True)
    
