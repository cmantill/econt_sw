import numpy as np
import logging
logging.basicConfig()
logger = logging.getLogger('latency')
logger.setLevel('DEBUG')

from utils.fast_command import FastCommands
from utils.link_capture import LinkCapture
lc = LinkCapture(logLevelLogger=30)
fc = FastCommands(logLevelLogger=30)

def find_BX0(lcapture,BX0_word=0xf922f922,BX0_position=None):
    """
    Finds the BX0s for each eTx
    """
    lc.configure_acquire([lcapture],"linkreset_ECONt",verbose=False)
    lc.do_capture([lcapture],verbose=False)
    fc.request("link_reset_econt")
    data = lc.get_captured_data([lcapture],verbose=False)[lcapture]
    
    BX0_rows,BX0_cols = (data == BX0_word).nonzero()
    # print(lcapture)
    ## print(BX0_rows)

    try:
        assert (len(BX0_rows) > 0) & np.any(BX0_cols==0)
    except AssertionError:
        logger.error('BX0 sync word not found anywhere or in link 0')
        return False
    return BX0_rows
        
def replace_latency(values,latency):
    values[values==-1] = latency
    return values

def match_BX0(latency_values,BX0_rows,BX0_position=None,neTx=13):
    """
    Checks if BX0 rows are all the same
    If BX0_position is not None, it checks that BX0 rows are at the same position as BX0_position
    """
    match = BX0_rows[:neTx] == BX0_rows[0]
    if BX0_position:
        match_pos = (BX0_rows[:neTx] == BX0_position)
        try:
            match_pos = match_pos | (BX0_rows[neTx:] == BX0_position)
        except:
            logger.info('BXO pos not found in last nlinks')
        match = match & match_pos
    return match

def scan_latency(lcapture,BX0_word=0xf922f922,neTx=13,
                 BX0_position=None,val=0):
    logger.info(f'Scan latency for {lcapture} for nlinks {neTx} with starting value {val}')
    foundBX0 = False
    latency = np.array([val] * lc.nlinks[lcapture])
    while not foundBX0:
        latency = replace_latency(latency,val)
        lc.set_latency([lcapture],latency)
        BX0_rows = find_BX0(lcapture,BX0_word,BX0_position=BX0_position)
        match = match_BX0(latency,BX0_rows,BX0_position,neTx)
        foundBX0 = np.all(match)
        latency[:neTx][~match] = -1
        if np.any(~match):
            latency[neTx:] = -1
        val += 1
    return latency,BX0_rows[0]

def align(BX0_word=0xf922f922,
          neTx=13,
          start_ASIC=0,start_emulator=0,
          latency_ASIC=None,latency_emulator=None):

    if latency_ASIC is not None:
        lc.set_latency(['lc-ASIC'],latency_ASIC)
    else:
        latency_ASIC,BX0_ASIC = scan_latency('lc-ASIC',BX0_word,val=start_ASIC,neTx=neTx)
        logger.info('Found latency for ASIC %s'%latency_ASIC)
        logger.info('Found BX0 word for ASIC %i'%BX0_ASIC)
    
    if latency_emulator is not None:
        lc.set_latency(['lc-emulator'],latency_emulator)
    else:
        latency_emulator,BX0_emulator = scan_latency('lc-emulator',BX0_word,BX0_position=BX0_ASIC,val=start_emulator,neTx=neTx)
        logger.info('Found latency for emulator %s '%latency_emulator)
        logger.info('Found BX0 word for emulator %i '%BX0_emulator)
