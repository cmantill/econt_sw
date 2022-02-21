import argparse

import logging
logging.basicConfig()
logger = logging.getLogger('i2c-addr')
logger.setLevel(logging.INFO)

from utils.asic_signals import ASICSignals

"""
Setting i2c address with uHal
Usage: python testing/set_i2c_address.py --i2c ASIC --addr 0
"""

if __name__ == "__main__":    
    parser = argparse.ArgumentParser(description='Set i2c address')
    parser.add_argument('--addr', type=int, default=0, help="address")
    parser.add_argument('--i2c',  type=str, choices=['ASIC', 'emulator'], help="key of i2c address to set")
    args = parser.parse_args()
    
    signals = ASICSignals()
    
    # set i2c address
    signals.set_i2caddr(args.i2c,args.addr)
