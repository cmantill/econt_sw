import argparse

import logging
logging.basicConfig()
logger = logging.getLogger('i2c-addr')
logger.setLevel(logging.INFO)

from utils.asic_signals import ASICSignals

"""
Setting i2c address with uHal
Usage: python testing/i2c_set_address.py --i2c ASIC --addr 0
"""

if __name__ == "__main__":    
    parser = argparse.ArgumentParser(description='Align links')
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE",default="")
    parser.add_argument('--addr', type=int, default=0, help="address")
    parser.add_argument('--i2c',  type=str, choices=['ASIC', 'emulator'], help="key of i2c address to set")
    args = parser.parse_args()
    
    signals = ASICSignals()
    
    # set i2c address
    signsls.set_i2caddr(args.i2c,args.addr)
