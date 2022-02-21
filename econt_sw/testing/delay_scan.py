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

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--io', type=str, default='from', help='IO block name')
    args = parser.parse_args()

    io = IOBlock(args.io,'IO')
    io.configure_IO(invert=True)
    bitcounts,errorcounts = io.delay_scan()
    
    print(bitcounts)
    print(errorcounts)
