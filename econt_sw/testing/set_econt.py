from i2c import call_i2c
import logging
logging.basicConfig()
logger = logging.getLogger(__name__)

from utils.io import IOBlock
from utils.fast_command import FastCommands
from utils.link_capture import LinkCapture
from utils.test_vectors import TestVectors

fc = FastCommands(logLevelLogger=30)
lc = LinkCapture(logLevelLogger=30)
tv = TestVectors(logLevelLogger=30)
from_io = IOBlock('from')
to_io = IOBlock('to')

# phase settings found for boards
phase_by_board = {
    2: "6,6,7,7,7,8,7,8,7,8,7,8",
    3: "7,6,8,7,0,8,8,0,8,8,9,8",
    7: "5,4,5,5,6,6,6,6,5,6,6,6",
    8: "5,4,5,5,6,6,6,6,5,6,6,6",
    9: "7,7,7,7,7,7,7,7,7,7,7,7",
    10: "7,7,7,7,7,7,7,7,7,7,7,7",
    11: "7,6,8,8,8,9,8,9,7,8,8,8",
    12: "7,7,7,7,7,7,7,7,7,7,7,7",
    13: "7,7,7,7,7,7,7,7,7,7,7,7",
    14: "7,7,7,7,7,7,7,7,7,7,7,7",
}
def set_phase(board):
    logger.info(f'Set fixed phase {phase_by_board[board]} for board {board}')
    call_i2c(args_name='EPRXGRP_TOP_trackMode',args_value=f'0',args_i2c='ASIC')
    call_i2c(args_name='CH_EPRXGRP_[0-11]_phaseSelect',args_value=f'{phase_by_board[board]}',args_i2c='ASIC')

def set_phase_of_enable(phase=0):
    logger.info(f'Set phase of enable {phase}')
    call_i2c(args_name="PLL_phase_of_enable_1G28",args_value=phase,args_i2c='ASIC')

def startup(write=True):
    call_i2c(args_yaml="configs/startup.yaml",args_i2c='ASIC,emulator',args_write=write)

def set_runbit(value=1):
    call_i2c(args_name="MISC_run",args_value=f'{value}',args_i2c='ASIC')

def read_status():
    x = call_i2c(args_name="FCTRL_locked,PUSM_state",args_i2c='ASIC')
    logger.info('FC status_locked: ',x['ASIC']['RO']['FCTRL_ALL']['status_locked'])
    logger.info('PUSM status: ',x['ASIC']['RO']['MISC_ALL']['misc_ro_0_PUSM_state'])

def set_fpga():
    fc.configure_fc()
    fc.set_bx("link_reset_roct",3500)
    fc.set_bx("link_reset_rocd",3501)
    fc.set_bx("link_reset_econt",3502)
    fc.set_bx("link_reset_econd",3503)

    tv.configure("PRBS28")
    tv.set_bypass(1)

    to_io.configure_IO(invert=True)
    from_io.configure_IO(invert=True)    
    
def word_align(bx,emulator_delay,bcr=0,verbose=True):
    set_fpga()

    import eRx
    eRx.linkResetAlignment(snapshotBX=bx,orbsyncVal=bcr,verbose=verbose,delay=emulator_delay,match_pattern="0xaccccccc9ccccccc")
    eRx.statusLogging(sleepTime=2,N=1)

def output_align():
    # set algo to threshold
    call_i2c(args_name="MFC_ALGORITHM_SEL_DENSITY_algo_select,ALGO_threshold_val_[0-47],FMTBUF_eporttx_numen,FMTBUF_tx_sync_word",
             args_value="0,[0x3fffff]*48,13,0x122",
             args_i2c="ASIC,emulator")

    to_io.configure_IO(invert=True)
    from_io.configure_IO(invert=True)
    from_io.reset_counters()
    align = from_io.check_IO(verbose=False)
    if align:
        from_io.manual_IO()

    import time
    # reset lc
    lc.reset(['lc-input','lc-ASIC','lc-emulator'])
    # configure acquire
    lc.configure_acquire(['lc-ASIC','lc-emulator'],"linkreset_ECONt")
    # send link reset econt
    fc.get_counter("link_reset_econt")
    fc.request("link_reset_econt")
    time.sleep(0.1)
    fc.get_counter("link_reset_econt")
    # check
    align = lc.check_links(['lc-ASIC'])
    if not align:
        logger.warning('lc-ASIC not aligned')
        # capture (improve)
        #python testing/eTx.py --capture --lc lc-ASIC --mode linkreset_ECONt --capture --csv
        exit()
    
    # need to improve latency finding
    from align_on_tester import modify_latency
    modify_latency(verbose=False)
    
    # do compare (improve)
    from eTx import compare_lc
    data = compare_lc()
