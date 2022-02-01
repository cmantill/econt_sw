import os
import uhal
from uhal_config import names,input_nlinks,output_nlinks

import logging
logging.basicConfig()
logger = logging.getLogger('utils')
logger.setLevel(logging.INFO)

def configure_fc(dev,read=False):
    """
    Configure FC
    Do not enable L1A (since this disables link resets)
    """
    if read:
        fc_stream = dev.getNode(names['fc']+".command.enable_fast_ctrl_stream").read()
        orb_sync = dev.getNode(names['fc']+".command.enable_orbit_sync").read()
        glob_l1a = dev.getNode(names['fc']+".command.global_l1a_enable").read()
        dev.dispatch()
        logger.info('fc stream %i orb_sync %i glob_l1a %i '%(fc_stream,orb_sync,glob_l1a))
    else:
        dev.getNode(names['fc']+".command.enable_fast_ctrl_stream").write(0x1);
        dev.getNode(names['fc']+".command.enable_orbit_sync").write(0x1);
        dev.getNode(names['fc']+".command.global_l1a_enable").write(0);
        dev.dispatch()
    
def enable_l1a(dev,read=False):
    if read:
        r =  dev.getNode(names['fc']+".command.global_l1a_enable").read()
        dev.dispatch()
        logger.info('glob_l1a %i '%r)
    else:
        dev.getNode(names['fc']+".command.global_l1a_enable").write(1);
        dev.dispatch()

def chipsync(dev):
    dev.getNode(names['fc']+".request.chipsync").write(1);
    dev.dispatch()

def send_l1a(dev):
    """
    Send L1A once
    """
    dev.getNode(names['fc']+".command.global_l1a_enable").write(0x1);
    dev.getNode(names['fc']+".periodic0.enable").write(0x0); # to get a L1A once
    #dev.getNode(names['fc']+".periodic0.enable").write(0x1); # to get a L1A every orbit
    dev.getNode(names['fc']+".periodic0.flavor").write(0); # 0 to get a L1A 
    dev.getNode(names['fc']+".periodic0.enable_follow").write(0); # does not depend on other generator                                                                                                  
    dev.getNode(names['fc']+".periodic0.bx").write(3500);
    dev.getNode(names['fc']+".periodic0.request").write(0x1);
    dev.dispatch()
    
    import time
    time.sleep(0.001)
    l1a_counter = dev.getNode(names['fc-recv']+".counters.l1a").read()
    dev.dispatch()
    logger.debug('L1A counter %i'%(int(l1a_counter)))
