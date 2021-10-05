import uhal
import argparse
import logging

logger = logging.getLogger('reset:test')
logger.setLevel(logging.INFO)

"""
Setting reset signals with uHal
Usage: python reset_signals.py --i2c ASIC --reset hard --release
"""

if __name__ == "__main__":    
    parser = argparse.ArgumentParser(description='Align links')
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE, NONE",default='NONE')
    parser.add_argument('--i2c',  type=str, choices=['ASIC', 'emulator'], help="key of i2c address to set")
    parser.add_argument('--reset',  type=str, choices=['hard', 'soft'], help="type of reset signal")
    parser.add_argument('--release', type=bool, default=False, help='release reset')

    args = parser.parse_args()

    # define uHal
    if args.logLevel.find("ERROR")==0:
        uhal.setLogLevelTo(uhal.LogLevel.ERROR)
    elif args.logLevel.find("WARNING")==0:
        uhal.setLogLevelTo(uhal.LogLevel.WARNING)
    elif args.logLevel.find("NOTICE")==0:
        uhal.setLogLevelTo(uhal.LogLevel.NOTICE)
    elif args.logLevel.find("DEBUG")==0:
        uhal.setLogLevelTo(uhal.LogLevel.DEBUG)
    elif args.logLevel.find("INFO")==0:
        uhal.setLogLevelTo(uhal.LogLevel.INFO)
    else:
        uhal.disableLogging()

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
    else:
        dev.getNode("ASIC-IO-I2C-I2C-fudge-0.resets.%s"%reset_string).write(0)
        dev.dispatch()
