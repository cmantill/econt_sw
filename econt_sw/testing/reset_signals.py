import argparse
import logging
from time import sleep
from utils.uhal_config  import set_logLevel

logging.basicConfig()
logger = logging.getLogger('reset')

from utils.reset_signals import ResetSignals

"""
Setting reset signals with uHal
Usage: python reset_signals.py --i2c ASIC --reset hard --release
"""

if __name__ == "__main__":    
    parser = argparse.ArgumentParser(description='Align links')
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE",default='INFO')
    parser.add_argument('--i2c',  type=str, default='ASIC', choices=['ASIC', 'emulator'], help="key of i2c address to set")
    parser.add_argument('--reset',  type=str, choices=['hard', 'soft'], help="type of reset signal")
    parser.add_argument('--hold', default=False, action='store_true', help='hold reset')
    parser.add_argument('--time', type=float, default=0.5, help='length of time to hold reset (default 0.5 seconds)')
    parser.add_argument('--repeat', type=int, default=None, help='send repeatedly N times')
    parser.add_argument('--release', default=False, action='store_true', help='release reset')
    parser.add_argument('--read', type=bool, default=False, help='read reset')

    args = parser.parse_args()

    set_logLevel(args)
    try:
        logger.setLevel(args.logLevel)
    except ValueError:
        logging.error("Invalid log level")
        exit(1)

    resets=ResetSignals()
    if args.repeat:
        resets.repeat_reset(reset=args.reset,
                            i2c=args.i2c,
                            sleepTime=args.time,
                            N=args.repeat)
    elif args.read:
        resets.read(reset=args.reset,
                    i2c=args.i2c)
    else:
        resets.send_reset(reset=args.reset,
                          i2c=args.i2c,
                          hold=args.hold,
                          release=args.release,
                          sleepTime=args.time)
