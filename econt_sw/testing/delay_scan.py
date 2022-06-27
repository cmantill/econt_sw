import time
import argparse

import logging
logging.basicConfig()
logger = logging.getLogger("delayScan")
logger.setLevel('INFO')
    
from utils.io import IOBlock

"""
Delay scan on IO blocks.

Usage:
   python testing/delay_scan.py --io from
"""

def delay_scan(odir,io='from'):
    io = IOBlock(io,'IO')
    io.configure_IO(invert=True)
    bitcounts,errorcounts = io.delay_scan(verbose=False)

    import os
    os.system(f'mkdir -p {odir}')
    import pickle
    with open(f'{odir}/{io}_io_delayscan.pkl','wb') as f:
        pickle.dump(errorcounts,f)

    from set_econt import io_align
    io_align()
    
    return errorcounts

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--io', type=str, default='from', help='IO block name')
    parser.add_argument('--odir', type=str, default='./', help='output dir') 
    args = parser.parse_args()

    delay_scan(args.odir,args.io)
