import os
import uhal
from .uhal_config import set_logLevel

import logging
logger = logging.getLogger('utils:pll_lock')
logger.setLevel(logging.INFO)
from time import sleep

""" Function to prevent initializing over and over """
def singleton(class_instance):
    instances = {}
    def get_instance(*args, **kwargs):
        key = (class_instance, tuple(args), tuple(kwargs.items()))
        if key not in instances:
            instances[key] = class_instance(*args, **kwargs)
        return instances[key]
    return get_instance

@singleton
class PLLLockCount:
    """Class to monitor PLL_LOCK_B transition counters on FPGA"""

    def __init__(self,logLevel=""):
        """Initialization class to setup connection manager and device"""
        set_logLevel(logLevel)

        self.man = uhal.ConnectionManager("file://connection.xml")
        self.dev = self.man.getDevice("mylittlememory")
        self.name = "ASIC-IO-Extra-IO-AXI-edge-counter-0"

    def getCount(self):
        PLL_switch_count = self.dev.getNode(self.name+".counter").read()
        self.dev.dispatch()
        return int(PLL_switch_count)

    def edgeSel(self,read=False,val=0):
        if read:
            edgeSelVal = self.dev.getNode(self.name+".edge_select").read()
            self.dev.dispatch()
            return int(edgeSelVal)
        else:
            self.dev.getNode(self.name+".edge_select").write(int(val))
            self.dev.dispatch()
        return

    def reset(self):
        self.dev.getNode(self.name+".clear_counter").write(1);
        self.dev.dispatch()
#        sleep(1)
        self.dev.getNode(self.name+".clear_counter").write(0);
        self.dev.dispatch()
