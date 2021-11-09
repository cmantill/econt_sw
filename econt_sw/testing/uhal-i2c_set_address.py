import uhal
import argparse
import logging

logger = logging.getLogger('i2c:test')
logger.setLevel(logging.INFO)

"""
Setting i2c address with uHal
Usage: python i2c_set_address.py --i2c ASIC --addr 0
"""

if __name__ == "__main__":    
    parser = argparse.ArgumentParser(description='Align links')
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE, NONE",default='NONE')
    parser.add_argument('--addr', type=int, default=0, help="address")
    parser.add_argument('--i2c',  type=str, choices=['ASIC', 'emulator'], help="key of i2c address to set")
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
    
    # set i2c address 
    dev.getNode("ASIC-IO-I2C-I2C-fudge-0.ECONT_%s_I2C_address"%args.i2c).write(args.addr);
    dev.dispatch()
