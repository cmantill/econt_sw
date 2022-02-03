import uhal
import argparse
import logging
from time import sleep
from utils.uhal_config  import set_logLevel

logging.basicConfig()
logger = logging.getLogger('reset')

"""
Setting reset signals with uHal
Usage: python reset_signals.py --i2c ASIC --reset hard --release
"""

if __name__ == "__main__":    
    parser = argparse.ArgumentParser(description='Align links')
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE, NONE",default='NONE')
    parser.add_argument('--i2c',  type=str, default='ASIC', choices=['ASIC', 'emulator'], help="key of i2c address to set")
    parser.add_argument('--reset',  type=str, choices=['hard', 'soft'], help="type of reset signal")
    parser.add_argument('--hold', default=False, action='store_true', help='hold reset')
    parser.add_argument('--time', type=float, default=0.5, help='length of time to hold reset (default 0.5 seconds)')
    parser.add_argument('--release', default=False, action='store_true', help='release reset')
    parser.add_argument('--read', type=bool, default=False, help='read reset')

    args = parser.parse_args()

    set_logLevel(args)
    try:
        logger.setLevel(args.logLevel)
    except ValueError:
        logging.error("Invalid log level")
        exit(1)
    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")
    
    if args.reset=='hard':
        # hard reset: go to state sleep mode, reset entire chip and all i2c is cleared
        reset_string = "ECONT_%s_RESETB"%args.i2c
    elif args.reset=='soft':
        # soft reset: same as hard reset but leaves i2c programmed
        reset_string = "ECONT_%s_SOFT_RESETB"%args.i2c
    else:
        logger.Error('No reset signal provided')

    if args.release:
        dev.getNode("ASIC-IO-I2C-I2C-fudge-0.resets.%s"%reset_string).write(1)
        dev.dispatch()
    elif args.hold:
        dev.getNode("ASIC-IO-I2C-I2C-fudge-0.resets.%s"%reset_string).write(0)
        dev.dispatch()
    elif args.read:
        reset = dev.getNode("ASIC-IO-I2C-I2C-fudge-0.resets.%s"%reset_string).read()
        dev.dispatch()
        print(reset_string, int(reset))
    else:
        dev.getNode("ASIC-IO-I2C-I2C-fudge-0.resets.%s"%reset_string).write(0)
        dev.dispatch()
        sleep(args.time)
        dev.getNode("ASIC-IO-I2C-I2C-fudge-0.resets.%s"%reset_string).write(1)
        dev.dispatch()
