import os
import uhal
import time
from .uhal_config import names

import logging
logging.basicConfig()
logger = logging.getLogger('utils:sc')
logger.setLevel(logging.INFO)

class StreamCompare():
    """Class to handle stream compare via uhal"""
     def __init__(self):
        """Initialization class to setup connection manager and device"""
        self.man = uhal.ConnectionManager("file://connection.xml")
        self.dev = self.man.getDevice("mylittlememory")
        self.sc = names['stream_compare']
        
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

    def configure_compare(self,nlinks=13,trigger=False):
        """
        Configure comparison lc-ASIC and lc-emulator
        """
        self.dev.getNode(self.sc+".control.active_links").write(nlinks)
        self.dev.dispatch()
    
        self.set_trigger(trigger)

    def reset_log_counters(self,stime=0.01):
        """
        Reset counters, wait for a time, latch them again.
        Log word and error count
        """
        # reset counters: set counters to zero and immediately continues counting as data comes in
        # latch counters: copies the current counter values to a separate set of registers that you can read out.
        #                 it  continues incrementing the counters, but the copies that you read out don't change (unless you tell it to latch again)
        self.dev.getNode(self.sc+".control.reset").write(0x1)
        self.dev.dispatch()
        time.sleep(stime)
        self.dev.getNode(self.sc+".control.latch").write(0x1)
        self.dev.dispatch()

        word_count = self.dev.getNode(self.sc+".word_count").read()
        err_count = self.dev.getNode(self.sc+".err_count").read()
        self.dev.dispatch()
        
        logger.info('Stream compare, word count %i, error count %i'%(word_count,err_count))
        return err_count
