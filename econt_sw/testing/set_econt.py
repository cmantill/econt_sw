from i2c import call_i2c

from utils.io import IOBlock
from utils.fast_command import FastCommands
from utils.link_capture import LinkCapture
from utils.test_vectors import TestVectors

fc = FastCommands()
lc = LinkCapture()
tv = TestVectors()
tv_bypass = TestVectors('bypass')
from_io = IOBlock('from')
to_io = IOBlock('to')

latency_dict = {
    3: 0, # repeater
    0: 0, # threshold
    1: 0, # STC
    2: 3, # BC
    4: 2, # AE
}

import logging
logger = logging.getLogger("set-econt")
logger.setLevel(logging.INFO)

# phase settings found for boards
phase_by_board = {
    2: "6,6,7,7,7,8,7,8,7,8,7,8",
    3: "7,6,8,7,0,8,8,0,8,8,9,8",
    7: "5,4,5,5,6,6,6,6,5,6,6,6",
    8: "5,4,5,5,6,6,6,6,5,6,6,6",
    9: "7,7,7,7,7,7,7,7,7,7,7,7",
    10: "7,7,7,7,7,7,7,7,7,7,7,7",
    11: "7,6,8,8,8,9,8,9,7,8,8,8",
    12: "8,8,9,9,9,10,9,10,9,9,9,10",
    13: "8,8,8,8,8,8,8,8,8,8,8,8",
    14: "7,7,7,7,7,7,7,7,7,7,7,7",
}
def set_phase(board=None,best_setting=None):
    call_i2c(args_name='EPRXGRP_TOP_trackMode',args_value=f'0',args_i2c='ASIC')
    phasesetting = best_setting
    if board is not None:
        phasesetting = phase_by_board[board]
    if phasesetting is not None:
        logging.debug(f'Set fixed phase {phasesetting}')
        call_i2c(args_name='CH_EPRXGRP_[0-11]_phaseSelect',args_value=f'{phasesetting}',args_i2c='ASIC')

def set_phase_of_enable(phase=0):
    logger.debug(f'Set phase of enable {phase}')
    call_i2c(args_name="PLL_phase_of_enable_1G28",args_value=phase,args_i2c='ASIC')

def startup(write=True):
    call_i2c(args_yaml="configs/startup.yaml",args_i2c='ASIC,emulator',args_write=write)

def set_runbit(value=1):
    call_i2c(args_name="MISC_run",args_value=f'{value}',args_i2c='ASIC')

def read_status():
    x = call_i2c(args_name="FCTRL_locked,PUSM_state",args_i2c='ASIC')
    logging.info('FC status_locked: %i'%x['ASIC']['RO']['FCTRL_ALL']['status_locked'])
    logging.info('PUSM status: %i'%x['ASIC']['RO']['MISC_ALL']['misc_ro_0_PUSM_state'])

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
    
def word_align(bx,emulator_delay,bcr=0,verbose=False):
    import eRx
    eRx.linkResetAlignment(snapshotBX=bx,orbsyncVal=bcr,verbose=verbose,delay=emulator_delay,match_pattern="0xaccccccc9ccccccc")
    eRx.statusLogging(sleepTime=2,N=1)

def io_align():
    tv.set_bypass(1)
    call_i2c(args_name="MFC_ALGORITHM_SEL_DENSITY_algo_select,ALGO_threshold_val_[0-47],FMTBUF_eporttx_numen,FMTBUF_tx_sync_word",
             args_value="0,[0x3fffff]*48,13,0x122",
             args_i2c="ASIC,emulator")
    to_io.configure_IO(invert=True)
    from_io.configure_IO(invert=True)
    from_io.reset_counters()
    align = from_io.check_IO(verbose=False)
    if align:
        from_io.manual_IO()

def output_align(verbose=False):
    import time
    # reset lc
    lc.reset(['lc-input','lc-ASIC','lc-emulator'])
    # configure acquire
    lc.configure_acquire(['lc-ASIC','lc-emulator'],"linkreset_ECONt")
    # send link reset econt
    fc.request("link_reset_econt")
    time.sleep(0.1)
    # check
    align = lc.check_links(['lc-ASIC'])
    if not align:
        logging.warning('lc-ASIC not aligned')
        exit()
    
    # find latency
    from latency import align
    align(verbose=False)
    
    # do compare (improve)
    from eTx import compare_lc
    data,err_count = compare_lc(verbose=False)
    if err_count>0:
        logging.warning(f'eTx error count after alignment: {err_count}')
    else:
        logging.info('Links are aligned between ASIC and emulator')

def bypass_align(idir="configs/test_vectors/alignment/",start_ASIC=0,start_emulator=1):
    # configure alignment inputs
    tv.configure("",idir,fname="testInput.csv")

    # configure RPT output via bypass
    rpt_dir = f"{idir}/RPT"
    tv_bypass.set_bypass(0)
    tv_bypass.configure("",rpt_dir,fname="testOutput.csv")  

    # configure RPT(13eTx) i2c for ASIC
    logging.debug(f"Configure ASIC w. {rpt_dir}/init.yaml")
    set_runbit(0)
    call_i2c(args_yaml=f"{rpt_dir}/init.yaml", args_i2c="ASIC,emulator", args_write=True)
    set_runbit(1)
    x=call_i2c(args_name='FMTBUF_eporttx_numen',args_write=False)
    num_links = x['ASIC']['RW']['FMTBUF_ALL']['config_eporttx_numen']
    logging.debug(f"Num links {num_links}")

    # then modify latency until we find pattern
    from latency import align
    align(BX0_word=0xffffffff,
          neTx=10,
          start_ASIC=start_ASIC,start_emulator=start_emulator)

def bypass_compare(idir,odir):
    # configure inputs
    tv.configure("",idir,fname="../testInput.csv",verbose=False)

    # configure outputs
    tv_bypass.set_bypass(0)
    tv_bypass.configure("",idir,fname="testOutput.csv",verbose=False)

    set_runbit(0)

    # configure i2c for ASIC
    logging.debug(f"Configure ASIC w. {idir}/init.yaml")
    call_i2c(args_yaml=f"{idir}/init.yaml", args_i2c="ASIC", args_write=True)

    # read nlinks
    x=call_i2c(args_name='FMTBUF_eporttx_numen',args_write=False)
    num_links = x['ASIC']['RW']['FMTBUF_ALL']['config_eporttx_numen']
    x=call_i2c(args_name='MFC_ALGORITHM_SEL_DENSITY_algo_select',args_write=False)
    algo = x['ASIC']['RW']['MFC_ALGORITHM_SEL_DENSITY']['algo_select']
    logging.debug(f"Num links {num_links} and algo {algo}")

    # modify latency
    latencies = lc.read_latency(['lc-ASIC','lc-emulator'])
    logging.debug("Latencies asic %s"%latencies['lc-ASIC'])
    logging.debug("Latencies emu %s"%latencies['lc-emulator'])
    new_latencies = [(lat + latency_dict[algo]) for lat in latencies['lc-emulator']]
    logging.debug("New Latencies %s"%new_latencies)
    lc.set_latency(['lc-emulator'],new_latencies)
    set_runbit(1)

    # compare words
    tag = idir.split("/")[-1]
    from eTx import compare_lc
    data,err_counts = compare_lc(nlinks=num_links,verbose=False,trigger=True,csv=True,odir=odir,fname=f"compare_{tag}")
    if err_counts:
        logging.warning(f'eTx error count after bypass comparison: {err_counts}')
    else:
        logging.info(f'eTx error count: {0}, for {idir} configuration')

    # set back latency
    lc.set_latency(['lc-emulator'],latencies['lc-emulator'])
