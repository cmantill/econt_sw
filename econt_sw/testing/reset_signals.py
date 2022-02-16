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

class ResetSignals:
    """
    Class for handling uhal reset signals
    """

    def __init__(self):
        """Initialization class to setup connection manager and device"""
        self.man = uhal.ConnectionManager("file://connection.xml")
        self.dev = self.man.getDevice("mylittlememory")

    def send_reset(self, reset='soft',i2c='ASIC', hold=False, release=False, sleepTime=0.5):
        """Send reset signal to device (either ASIC or emulator), either soft or hard reset
        """
        if reset=='hard':
            # hard reset: go to state sleep mode, reset entire chip and all i2c is cleared
            reset_string = "ECONT_%s_RESETB"%i2c
        elif reset=='soft':
            # soft reset: same as hard reset but leaves i2c programmed
            reset_string = "ECONT_%s_SOFT_RESETB"%i2c
        else:
            logger.Error('No reset signal provided')

        if hold:
            self.dev.getNode("ASIC-IO-I2C-I2C-fudge-0.resets.%s"%reset_string).write(0)
            self.dev.dispatch()
        elif release:
            self.dev.getNode("ASIC-IO-I2C-I2C-fudge-0.resets.%s"%reset_string).write(1)
            self.dev.dispatch()
        else:
            self.dev.getNode("ASIC-IO-I2C-I2C-fudge-0.resets.%s"%reset_string).write(0)
            self.dev.dispatch()
            sleep(sleepTime)
            self.dev.getNode("ASIC-IO-I2C-I2C-fudge-0.resets.%s"%reset_string).write(1)
            self.dev.dispatch()

    def repeat_reset(self,reset='soft',i2c='ASIC', sleepTime=0.5, N=2):
        """Send repeated reset signals N times"""
        for i in range(N):
            self.send_reset(reset=reset,
                            i2c=i2c,
                            sleepTime=sleepTime)
            sleep(sleepTime)

    def read(self,reset='soft',i2c='ASIC',verbose=True):
        """Read current state of reset line"""
        if reset=='hard':
            # hard reset: go to state sleep mode, reset entire chip and all i2c is cleared
            reset_string = "ECONT_%s_RESETB"%i2c
        elif reset=='soft':
            # soft reset: same as hard reset but leaves i2c programmed
            reset_string = "ECONT_%s_SOFT_RESETB"%i2c
        else:
            logger.Error('No reset signal provided')

        resetStatus = self.dev.getNode("ASIC-IO-I2C-I2C-fudge-0.resets.%s"%reset_string).read()
        self.dev.dispatch()
        if verbose:
            print(reset_string, int(resetStatus))
        return resetStatus

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
