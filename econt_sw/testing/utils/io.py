import os
import uhal
from .uhal_config import *
import time

import logging

class IOBlock:
    """ Class to handle IO blocks via uhal """

    def __init__(self,io,io_name='IO',logLevel=""):
        """Initialization class to setup connection manager and device"""
        set_logLevel(logLevel)
        
        self.man = uhal.ConnectionManager(connection_filename)
        self.dev = self.man.getDevice(deviceName)
        self.name = names[io_name][io]
        self.io = io
        self.io_name = io_name
        self.nlinks = input_nlinks if io=='to' else output_nlinks

        self.logger = logging.getLogger('utils:IO')

    def reset_counters(self):
        """Resets counters"""
        # resets the counters (it will clear itself)
        self.dev.getNode(self.name+".global.global_reset_counters").write(0x1)
        time.sleep(0.01)
        # latches counters (saves counter values for all links)
        self.dev.getNode(self.name+".global.global_latch_counters").write(0x1)
        self.dev.dispatch()
        for l in range(self.nlinks):
            self.dev.getNode(self.name+".link"+str(l)+"."+"reg0.reset_counters").write(1)
            self.dev.getNode(self.name+".link"+str(l)+"."+"reg0.latch_counters").write(1)
        self.dev.dispatch()

    def configure_IO(self,invert=False):
        """Configures IO blocks to automatic delay setting"""
        ioblock_settings = {
            "reg0.tristate_IOBUF": 0,
            "reg0.bypass_IOBUF": 0,
            "reg0.invert": 0,
            "reg0.reset_link": 0,
            "reg0.reset_counters": 1,
            "reg0.delay_mode": 0, 
        }

        # set delay mode to 1 to those blocks that need to be aligned
        if (self.io_name == "ASIC-IO" and self.io=="to") or (self.io_name == "IO" and self.io=="from"):
            ioblock_settings["reg0.delay_mode"] = 1
            delay_mode = 1

        # set invert to 1
        if invert:
            ioblock_settings["reg0.invert"] = 1
            
        # set 
        for l in range(self.nlinks):
            for key,value in ioblock_settings.items():
                self.dev.getNode(self.name+".link"+str(l)+"."+key).write(value)
            self.dev.dispatch()

        # reset links
        self.dev.getNode(self.name+".global.global_rstb_links").write(0x1)
        self.dev.dispatch()

        # reset counters
        self.reset_counters()

    def get_delay(self,verbose=True):
        """Reads delay P and N"""
        delay_P = {}
        delay_N = {}
        for link in range(self.nlinks):
            delay_out = self.dev.getNode(self.name+".link%i"%link+".reg3.delay_out").read()
            delay_out_N = self.dev.getNode(self.name+".link%i"%link+".reg3.delay_out_N").read()
            self.dev.dispatch()
            delay_P[link] = int(delay_out)
            delay_N[link] = int(delay_out_N)

        self.logger.debug("P-side delay setting: %s, Eye width: %s"%(delay_P,delay_N))

        return delay_P,delay_N

    def set_delay(self,delay_P):
        """Sets delay given delay array"""
        for l in range(self.nlinks):
            self.dev.getNode(self.name+".link"+str(l)+".reg0.delay_mode").write(0)
            self.dev.getNode(self.name+".link"+str(l)+".reg0.delay_in").write(delay_P[l])
            self.dev.getNode(self.name+".link"+str(l)+".reg0.delay_offset").write(8) # fix this to 8
            self.dev.getNode(self.name+".link"+str(l)+".reg0.delay_set").write(1)
        self.dev.dispatch()
        
    def manual_IO(self):
        """Configures manual delay setting"""
        # read delays found by automatic delay setting
        delay_P,delay_N = self.get_delay(verbose=False)

        # set delay mode to 0 and delays to what we found
        self.set_delay(delay_P)

        # reset counters
        self.reset_counters()
        
    def delay_scan(self,verbose=False):
        bitcounts = {}
        errorcounts = {}
        for l in range(self.nlinks):
            bitcounts[l] = []
            errorcounts[l] = []
        
        # scan over P and N delays
        for delay in range(0,504,8):
            # set delays
            delay = 0 if delay<0 else delay
            delay = 503 if delay>503 else delay # 503+8=511
            # self.logger.debug(f"Set delay to {delay}")

            self.set_delay([delay]*self.nlinks)

            # TODO: do we need to wait until delay is ready?

            # reset counters
            self.reset_counters()

            # read bit counter and error counter
            for l in range(self.nlinks):
                error_counter = self.dev.getNode(self.name+".link"+str(l)+".error_counter").read()
                bit_counter = self.dev.getNode(self.name+".link"+str(l)+".bit_counter").read()
                self.dev.dispatch()
                bitcounts[l].append(int(bit_counter))
                errorcounts[l].append(int(error_counter))

        self.align_delay_vals()

        return bitcounts,errorcounts
    
    def align_delay_vals(self):
        for l in range(self.nlinks):
            self.dev.getNode(self.name+".link"+str(l)+".reg0.delay_mode").write(1)
        self.manual_IO()

    def print_IO(self):
        """Prints IO block configuration"""
        regs = ["reg0.reset_link","reg0.reset_counters","reg0.delay_mode","reg0.delay_set",
                "reg0.bypass_IOBUF","reg0.tristate_IOBUF","reg0.latch_counters",
                "reg0.delay_in","reg0.delay_offset","reg0.invert",
                "bit_counter","error_counter",
                "reg3.delay_ready","reg3.delay_out","reg3.delay_out_N","reg3.waiting_for_transitions",
                ]
        for l in range(self.nlinks):
            vals = {}
            for reg in regs:
                tmp = self.dev.getNode(self.name+".link"+str(l)+"."+reg).read()
                self.dev.dispatch()
                vals[reg] = int(tmp)
            self.logger.info("%s-IO link%i: %s"%(self.io,l,vals))

    def check_IO(self,nit=10,verbose=False):
        """ Checks whether IO block is aligned """

        # reset the counters
        self.reset_counters()
        
        # check the counters
        IO_delayready = []
        for l in range(self.nlinks):
            i=0
            delay_ready=0
            while i < nit:
                i+=1
                bit_tr = self.dev.getNode(self.name+".link"+str(l)+".reg3.waiting_for_transitions").read()
                delay_ready = self.dev.getNode(self.name+".link"+str(l)+".reg3.delay_ready").read()
                error_counter = self.dev.getNode(self.name+".link"+str(l)+".error_counter").read()
                bit_counter = self.dev.getNode(self.name+".link"+str(l)+".bit_counter").read()
                self.dev.dispatch()
                if verbose or error_counter>0:
                    self.logger.debug("%s-IO link%i: bit_tr %d, delay ready %d, error counter %i, bit_counter %i"%(self.io,l,bit_tr,delay_ready,error_counter,bit_counter))
                if delay_ready == 1:
                    break
            IO_delayready.append(delay_ready)

        is_aligned = True
        for delay in IO_delayready:
            if delay!=1:
                is_aligned = False

        if is_aligned:
            self.logger.debug("Links %s-IO are aligned"%self.io)
        else:
            self.logger.warning("Links %s-IO are not aligned"%self.io)
        return is_aligned
