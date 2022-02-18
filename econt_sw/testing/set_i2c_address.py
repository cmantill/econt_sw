import uhal
import argparse
import logging
from utils.uhal_config  import set_logLevel

logging.basicConfig()
logger = logging.getLogger('i2cSet')

"""
Setting i2c address with uHal
Usage: python3 set_i2c_address.py --i2c ASIC --addr 0
"""

if __name__ == "__main__":    
    parser = argparse.ArgumentParser(description='Align links')
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE",default='INFO')
    parser.add_argument('--addr', type=int, default=0, help="address")
    parser.add_argument('--i2c',  type=str, choices=['ASIC', 'emulator'], help="key of i2c address to set")
    args = parser.parse_args()

    set_logLevel(args)
    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")

    try:
        logger.setLevel(args.logLevel)
    except ValueError:
        logging.error("Invalid log level")
        exit(1)

    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")
    
    # set i2c address 
    logger.info("Writing to ASIC-IO-I2C-I2C-fudge-0.ECONT_%s_I2C_address "%args.i2c,args.addr)
    dev.getNode("ASIC-IO-I2C-I2C-fudge-0.ECONT_%s_I2C_address"%args.i2c).write(args.addr)
    dev.dispatch()
