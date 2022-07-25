import numpy as np

import logging

from utils.fast_command import FastCommands
from utils.link_capture import LinkCapture
lc = LinkCapture()
fc = FastCommands()

def find_BX0(lcapture,BX0_word=0xf922f922,BX0_position=None):
    """
    Finds the BX0s for each eTx
    """
    lc.configure_acquire([lcapture],"linkreset_ECONt",verbose=False)
    lc.do_capture([lcapture],verbose=False)
    fc.request("link_reset_econt")
    data = lc.get_captured_data([lcapture],verbose=False)[lcapture]
    
    BX0_rows,BX0_cols = (data == BX0_word).nonzero()

    try:
        assert (len(BX0_rows) > 0) & np.any(BX0_cols==0)
        logging.info('Found alignment word for %s in BX0_rows: %s'%(lcapture,list(BX0_rows)))
    except AssertionError:
        logging.error('BX0 sync word not found anywhere or in link 0')
        return False

    return BX0_rows
        
def replace_latency(values,latency):
    values[values==-1] = latency
    return values

def match_BX0(latency_values,BX0_rows,BX0_position=None,neTx=13):
    """
    Checks if BX0 word is found for all neTx
    If we have a position to compare to (BX0_position) it checks that all eTx match that position.
    """
    match = (BX0_rows[:neTx] == BX0_rows[0]) | (BX0_rows[-neTx:] == BX0_rows[-neTx])
    new_BX0_position = None
    if np.all(match):
        logging.info('Found a match of all BX0')
        if BX0_position is not None:
            match_pos = (BX0_rows[:neTx] == BX0_position) | (BX0_rows[-neTx:] == BX0_position)
            match = match & match_pos
            if np.all(~match_pos):
                logging.info('BX0 does not match the reference BX0 position')
                # check that the position of BX0 is not > BX0_position
                if np.all(BX0_rows[:neTx] == BX0_rows[0]) and (BX0_position - BX0_rows[0] < 0):
                    new_BX0_position = BX0_rows[0]
                    logging.info(f'New position is {new_BX0_position}')
                elif np.all(BX0_rows[-neTx:] == BX0_rows[-neTx]) and (BX0_position - BX0_rows[-neTx] < 0):
                    new_BX0_position = BX0_rows[-neTx]
                    logging.info(f'New position is {new_BX0_position}')
            else:
                logging.info('Found a match of all BX0 and the reference BX0 position')
                new_BX0_position = BX0_position
        else:
            if np.all(BX0_rows[:neTx] == BX0_rows[0]): new_BX0_position = BX0_rows[0]
            if np.all(BX0_rows[-neTx:] == BX0_rows[-neTx]): new_BX0_position = BX0_rows[-neTx]
    return match,new_BX0_position

def scan_latency(lcapture,BX0_word=0xf922f922,neTx=13,
                 BX0_position=None,
                 val=0):
    logging.debug(f'Scan latency for {lcapture} for nlinks {neTx} with starting value {val} and BX0 position {BX0_position}')
    latency = np.array([val] * lc.nlinks[lcapture])
    for val in range(val,30):
        logging.debug(f'Setting latency for {lcapture} to {val}')
        latency = replace_latency(latency,val)
        lc.set_latency([lcapture],latency)
        BX0_rows = find_BX0(lcapture,BX0_word,BX0_position=BX0_position)
        match,new_BX0 = match_BX0(latency,BX0_rows,BX0_position,neTx)
        latency[:neTx][~match] = -1
        if np.any(~match):
            latency[neTx:] = -1
        if new_BX0:
            BX0_position = new_BX0
            break 
    if BX0_position is None:
        logging.warning(f'No BX0 found for {lcapture}')

    return latency,BX0_position

def align(BX0_word=0xf922f922,
          neTx=13,
          start_ASIC=0,start_emulator=0,
          latency_ASIC=None,latency_emulator=None):

    if latency_ASIC is not None:
        lc.set_latency(['lc-ASIC'],latency_ASIC)
    else:
        latency_ASIC,BX0_ASIC = scan_latency('lc-ASIC',BX0_word,val=start_ASIC,neTx=neTx)
        if BX0_ASIC is None:
            logging.error('No BX0 word found for ASIC during latency alignment')
            exit()
        else:
            logging.debug('Found latency for ASIC %s'%latency_ASIC)
            logging.debug('Found BX0 word for ASIC %i'%BX0_ASIC)
    
    if latency_emulator is not None:
        lc.set_latency(['lc-emulator'],latency_emulator)
    else:
        latency_emulator,BX0_emulator = scan_latency('lc-emulator',BX0_word,
                                                       BX0_position=BX0_ASIC,val=start_emulator,neTx=neTx)
        if(BX0_emulator != BX0_ASIC):
            logging.info('Trying to find ASIC again')
            latency_ASIC,BX0_ASIC = scan_latency('lc-ASIC',BX0_word,BX0_position=BX0_emulator,val=start_ASIC,neTx=neTx)
        else:
            logging.debug('Found latency for emulator %s '%latency_emulator)
            logging.debug('Found BX0 word for emulator %i '%BX0_emulator)

    return True
