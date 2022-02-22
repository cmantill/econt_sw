from i2c import call_i2c
import numpy as np
import argparse
import os

from time import sleep
import datetime

from utils.asic_signals import ASICSignals
from utils.fast_command import FastCommands
from utils.test_vectors import TestVectors

from utils.uhal_config  import set_logLevel
import logging
set_logLevel()
logging.basicConfig()
logger = logging.getLogger('Aligner')

# logger.setLevel(logging.INFO)
# ch = logging.StreamHandler()
# ch.setLevel(logging.INFO)
# logger.addHandler(ch)

from eRx import checkWordAlignment, checkSnapshots

tv = TestVectors()
resets = ASICSignals()
fc = FastCommands()

def autoAlignment(snapshotBX=3, check=True, verbose=False):
    """
    Performs automatic alignment sequence.
    Sets minimum i2c settings required for alignment, then issues a link_reset_roct fast command
    """

    call_i2c(args_name='CH_ALIGNER_[0-11]_per_ch_align_en,ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,ALIGNER_snapshot_arm,ALIGNER_orbsyn_cnt_snapshot,ALIGNER_orbsyn_cnt_load_val',args_value=f'[1]*12,0,1,1,{snapshotBX},0')
    fc.request('link_reset_roct')
    if check:
        status=checkWordAlignment(verbose=False,ASIC_only=True)

        if status==False:
            checkWordAlignment(verbose=True,ASIC_only=True)
        else:
            print('Good Alignment')

def alignmentDelayScan():
    delays = [0]*12

    pattern_0 = 0x9ccccccc
    pattern_x = 0xaccccccc

    data=np.array([pattern_x]*12*3564,dtype=int).reshape(12,3564)
    data[:,0]=pattern_0
    dataBin = np.vectorize(lambda x: f'{x:032b}')(data)

    for eRx in range(1):
        delays = [0]*12
        for x in range(-32,128):#[1,2,3,4,8,16,32,64,128]:#[-32,-16,-1,0,1,16,32]:
            delays[eRx] = x
            for l in range(12):
                d=delays[l]-8
                bitStream = ''.join(dataBin[l])
                bitStream = bitStream[d:]+bitStream[:d]
                data[l,:]=[int(bitStream[x:x+32],2) for x in range(0, 32*3564,32)]
            print(f'Testing delays {delays}')
            tv.configure(dtype='pattern',pattern=data,n_idle_words=0,verbose=False)
            autoAlignment(snapshotBX=3,check=True,verbose=True)


if __name__=="__main__":
#    autoAlignment()
    alignmentDelayScan()

