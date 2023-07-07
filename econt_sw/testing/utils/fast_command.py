import os
import uhal
from .uhal_config import names,set_logLevel,connection_filename,deviceName

import logging

class FastCommands:
    """Class to handle sending fast command signals over uhal"""

    def __init__(self,logLevel=""):
        """Initialization class to setup connection manager and device"""
        set_logLevel(logLevel)
        
        self.man = uhal.ConnectionManager(connection_filename)
        self.dev = self.man.getDevice(deviceName)
        self.name = names['fc']
        self.name_recv = names['fc-recv']
        
        self.logger = logging.getLogger('utils:fc')

    def fc_stream(self,value=1):
        self.dev.getNode(self.name+".command.enable_fast_ctrl_stream").write(value);
        self.dev.dispatch()

    def configure_fc(self,read=False):
        """
        Configure FC.
        Do not enable L1A (since this disables link resets)
        """
        if read:
            fc_stream = self.dev.getNode(self.name+".command.enable_fast_ctrl_stream").read()
            orb_sync = self.dev.getNode(self.name+".command.enable_orbit_sync").read()
            glob_l1a = self.dev.getNode(self.name+".command.global_l1a_enable").read()
            self.dev.dispatch()
            self.logger.info('FC status: fc stream %i orb_sync %i glob_l1a %i '%(fc_stream,orb_sync,glob_l1a))
        else:
            self.dev.getNode(self.name+".command.enable_fast_ctrl_stream").write(0x1);
            self.dev.getNode(self.name+".command.enable_orbit_sync").write(0x1);
            self.dev.getNode(self.name+".command.global_l1a_enable").write(0);
            self.dev.dispatch()
    
    def enable_l1a(self,read=False):
        if read:
            r =  self.dev.getNode(self.name+".command.global_l1a_enable").read()
            self.dev.dispatch()
            self.logger.info('Enable-L1A %i '%r)
        else:
            self.dev.getNode(self.name+".command.global_l1a_enable").write(1);
            self.dev.dispatch()

    def set_bx(self,fc,bx):
        # self.logger.debug(f'{fc}: {bx}')
        self.dev.getNode(self.name+".bx_"+fc).write(bx)
        self.dev.dispatch()

    def get_bx(self,fc):
        r=self.dev.getNode(self.name+".bx_"+fc).read()
        self.dev.dispatch()
        return r

    def request(self,fc,verbose=False):
        """
        Request fast command.
        Options: chipsync,
        """
        self.dev.getNode(self.name+".request."+fc).write(1);
        self.dev.dispatch()
        if verbose:
            self.logger.info(f'Request {fc}')

    def get_counter(self,fc,verbose=True):
        counter = self.dev.getNode(self.name_recv+".counters."+fc).read()
        self.dev.dispatch()
        if verbose:
            self.logger.info('%s counter %i'%(fc,int(counter)))
        return int(counter)
        
    def read_command_delay(self):
        d = self.dev.getNode(self.name+".command_delay").read();
        self.dev.dispatch()
        self.logger.info('Command delay %i'%int(d))

    def set_command_delay(self):
        self.dev.getNode(self.name+".command_delay").write(1);
        self.dev.dispatch()

    def send_l1a(self):
        """
        Send L1A once
        """
        self.dev.getNode(self.name+".command.global_l1a_enable").write(0x1);
        self.dev.getNode(self.name+".periodic0.enable").write(0x0); # to get a L1A once
        #self.dev.getNode(self.name+".periodic0.enable").write(0x1); # to get a L1A every orbit
        self.dev.getNode(self.name+".periodic0.flavor").write(0); # 0 to get a L1A 
        self.dev.getNode(self.name+".periodic0.enable_follow").write(0); # does not depend on other generator
        self.dev.getNode(self.name+".periodic0.bx").write(3500);
        self.dev.getNode(self.name+".periodic0.request").write(0x1);
        self.dev.dispatch()
    
        import time
        time.sleep(0.001)
        l1a_counter = self.dev.getNode(self.name_recv+".counters.l1a").read()
        self.dev.dispatch()
        self.logger.debug('L1A counter %i'%(int(l1a_counter)))
