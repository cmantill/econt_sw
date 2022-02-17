import uhal
import logging
from time import sleep

logging.basicConfig()
logger = logging.getLogger('reset')

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
