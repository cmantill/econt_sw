import uhal
from time import sleep
from utils.uhal_config import set_logLevel,names,connection_filename, deviceName

import logging

class ASICSignals:
    """
    Class for handling uhal ASIC signals
    """

    def __init__(self,logLevel=""):
        """Initialization class to setup connection manager and device"""
        set_logLevel(logLevel)
        self.man = uhal.ConnectionManager(connection_filename)
        self.dev = self.man.getDevice(deviceName)
        self.name = "ASIC-IO-I2C-I2C-fudge-0"
        self.name_delay = names['delay']
        self.name_clock = "housekeeping-AXI-mux-0"
        self.logger = logging.getLogger('utils:ASIC')

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
            self.logger.Error('No reset signal provided')

        if hold:
            self.dev.getNode(self.name + ".resets." + reset_string).write(0)
            self.dev.dispatch()
        elif release:
            self.dev.getNode(self.name + ".resets." + reset_string).write(1)
            self.dev.dispatch()
        else:
            self.dev.getNode(self.name + ".resets." + reset_string).write(0)
            self.dev.dispatch()
            sleep(sleepTime)
            self.dev.getNode(self.name + ".resets." + reset_string).write(1)
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
            self.logger.error('No reset signal provided')
            return

        resetStatus = self.dev.getNode(self.name + ".resets." + reset_string).read()
        self.dev.dispatch()
        if verbose:
            print(reset_string, int(resetStatus))
        return resetStatus

    def set_i2caddr(self,i2c,addr):
        self.logger.info("Writing to ASIC-IO-I2C-I2C-fudge-0.ECONT_%s_I2C_address "%i2c,addr)
        self.dev.getNode(self.name + ".ECONT_%s_I2C_address"%i2c).write(addr)
        self.dev.dispatch()
        
    def set_clock(self,clock=0):
        self.dev.getNode(self.name_clock+".select").write(clock);
        self.dev.dispatch()

    def set_delay(self,delay):
        self.dev.getNode(self.name_delay+".delay").write(delay)
        self.dev.dispatch()
