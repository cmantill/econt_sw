import time
import argparse

import logging
logging.basicConfig()
logger = logging.getLogger('check')
logger.setLevel('INFO')

from utils.io import IOBlock
from utils.link_capture import LinkCapture

from_io = IOBlock('from')
to_io = IOBlock('to')
lc = LinkCapture()

"""
Check alignment on different blocks

Usage:
   python testing/check_block.py --check --block [from-IO,to-IO,lc-ASIC,lc-emulator]
"""

def check_align(block):
    if block=='from-IO':
        from_io.reset_counters()
        align = from_io.check_IO()
    elif block=='to-IO':
        align = to_io.check_IO()
    elif block=='lc-ASIC':
        align = lc.check_links(['lc-ASIC'])
    return align

def print_block(block):
    if block=='from-IO':
        from_io.print_IO()
        from_io.get_delay(verbose=True)
    elif block=='to-IO':
        to_io.parint_IO()
        to_io.get_delay(verbose=True)
    elif block=='lc-ASIC':
        lc.check_lc(['lc-ASIC'])
    elif block=='latency':
        lc.read_latency(['lc-ASIC','lc-emulator'])

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', default=False, help='check that block is aligned')
    parser.add_argument('--nlinks', type=int, default=-1, help='number of links')
    parser.add_argument('-B', '--block', dest='block', required=True)
    args = parser.parse_args()
            
    if args.check:
        check_align(args.block)
    else:
        print_block(args.block)
