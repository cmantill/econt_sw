import os
import time

import uhal
from .uhal_config import names,set_logLevel,connection_filename,deviceName

import logging

class StreamCompare():
    """Class to handle stream compare via uhal"""
    def __init__(self,logLevel="",logLevelLogger=10):
        """Initialization class to setup connection manager and device"""
        set_logLevel(logLevel)
        
        self.man = uhal.ConnectionManager(connection_filename)
        self.dev = self.man.getDevice(deviceName)
        self.sc = names['stream_compare']

        self.logger = logging.getLogger('utils:sc')
        # self.logger.setLevel(logLevelLogger)
        
    def set_trigger(self,trigger=False):
        """
        - While trigger is 0, it will not generate L1A at all (but of course it will not impede other sources of L1A, either) 
        - While trigger is 1, stream_compare will generate L1A (only for the link capture blocks) on every BX where it sees a mismatch 
        """
        if trigger:
            self.dev.getNode(self.sc+".trigger").write(0x1)
        else:
            self.dev.getNode(self.sc+".trigger").write(0x0)
        self.dev.dispatch()
        
    def set_links(self,nlinks=13):
        self.dev.getNode(self.sc+".control.active_links").write(nlinks)
        self.dev.dispatch()

    def configure_compare(self,nlinks=13,trigger=False):
        """
        Configure comparison lc-ASIC and lc-emulator
        """
        self.set_links(nlinks)
        self.set_trigger(trigger)

    def reset_counters(self):
        """Set counters to zero and immediately continues counting as data comes in"""
        self.dev.getNode(self.sc+".control.reset").write(0x1)
        self.dev.dispatch()

    def latch_counters(self):
        """
        Copies the current counter values to a separate set of registers that you can read out.
        It continues incrementing the counters, but the copies that you read out don't change (unless you tell it to latch again).
        The counters roll over at 2^32
        """
        self.dev.getNode(self.sc+".control.latch").write(0x1)
        self.dev.dispatch()

    def read_counters(self,verbose=True):
        word_count = self.dev.getNode(self.sc+".word_count").read()
        err_count = self.dev.getNode(self.sc+".err_count").read()
        self.dev.dispatch()
        if verbose:
            self.logger.info('Word count %i, error count %i'%(word_count,err_count))
        return err_count

    def reset_log_counters(self,stime=0.01,verbose=True):
        """
        Reset counters, wait for a time, latch them again.
        Log word and error count.
        SC just compares the two inputs: If they match, then it increments the word counter, and doesn't do anything else.
        If they don't match, then it increments both the word and error counters, and, if it is set to do triggering, then it sets its "mismatch" output to 1 for one clock cycle (otherwise it is 0).
        """
        self.reset_counters()
        time.sleep(stime)
        self.latch_counters()
        err_count = self.read_counters(verbose)
        return err_count
