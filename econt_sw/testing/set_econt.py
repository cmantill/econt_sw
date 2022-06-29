from i2c import call_i2c

from utils.io import IOBlock
from utils.fast_command import FastCommands
from utils.link_capture import LinkCapture
from utils.test_vectors import TestVectors
from utils.stream_compare import StreamCompare
from utils.asic_signals import ASICSignals

signals=ASICSignals()
fc = FastCommands()
lc = LinkCapture()
tv = TestVectors()
tv_bypass = TestVectors('bypass')
from_io = IOBlock('from')
to_io = IOBlock('to')
sc = StreamCompare()

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
    from eRx import checkWordAlignment,statusLogging

    verbose=True
    def setAlignment(snapshotBX=None, delay=None):
        if snapshotBX is not None:
            call_i2c(args_name='ALIGNER_orbsyn_cnt_snapshot',args_value=f'{snapshotBX}',args_i2c='ASIC,emulator')
        if delay is not None:
            signals.set_delay(delay)
        fc.request('link_reset_roct')

    match_pattern = "0xaccccccc9ccccccc"
    snapshotBX=bx
    delay=emulator_delay
    orbsyncVal=bcr

    call_i2c(args_name='CH_ALIGNER_[0-11]_per_ch_align_en',args_value='1',args_i2c='ASIC,emulator')
    call_i2c(args_name='CH_ALIGNER_[0-11]_sel_override_en,CH_ALIGNER_[0-11]_patt_en,CH_ALIGNER_[0-11]_prbs_chk_en',
             args_value='0', args_i2c='ASIC,emulator')
    call_i2c(args_name='ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,ALIGNER_snapshot_arm',
             args_value=f'0,1,1',args_i2c='ASIC,emulator')
    call_i2c(args_name='ALIGNER_match_pattern_val,ALIGNER_match_mask_val',
             args_value=f'{match_pattern},0',
             args_i2c='ASIC,emulator')

    fc.configure_fc()
    fc.set_bx("link_reset_roct",3500)

    if snapshotBX is None:
        # loop over snapshot BX
        goodASIC = False
        for snapshotBX in [2,3,4,5,1,0,6,7,8,9]:
            setAlignment(snapshotBX,delay=0)
            goodASIC,_ = checkWordAlignment(verbose=verbose,match_pattern=match_pattern,ASIC_only=True)
            if goodASIC:
                break
        if not goodASIC:
            logger.error('Unable to find good snapshot bx')
            exit()

        goodEmulator = False
        for delay in [snapshotBX+1, snapshotBX, snapshotBX-1, snapshotBX+2, snapshotBX-2]:
            setAlignment(delay=delay)
            _,goodEmulator = checkWordAlignment(verbose=verbose,match_pattern=match_pattern)
            if goodEmulator:
                break
        if not goodEmulator:
            logger.error('Unable to find good delay setting')
            exit()
    else:
        # just set the parameters and check alignment
        setAlignment(snapshotBX,delay)
        goodASIC,goodEmulator = checkWordAlignment(verbose=verbose,match_pattern=match_pattern)

    if goodASIC and goodEmulator:
        logger.info(f'Good input word alignment, snapshotBX {snapshotBX} and delay {delay}')

    statusLogging(sleepTime=2,N=1)

def output_align(verbose=False):
    tv.set_bypass(1)
    call_i2c(args_yaml="configs/alignOutput_TS.yaml",args_i2c='ASIC,emulator',args_write=True)

    x=call_i2c(args_name='FMTBUF_eporttx_numen',args_i2c="ASIC,emulator",args_write=False)
    num_links_asic = x['ASIC']['RW']['FMTBUF_ALL']['config_eporttx_numen']
    num_links_emu = x['emulator']['RW']['FMTBUF_ALL']['config_eporttx_numen']
    logging.debug(f"Num links {num_links_asic} {num_links_emu}")

    for phase_of_enable in [0,4]:
        logging.debug(f'Aligning ASIC: Setting phase of enable to {phase_of_enable}')
        set_phase_of_enable(f'{phase_of_enable}')

        to_io.configure_IO(invert=True)
        from_io.configure_IO(invert=True)
        from_io.reset_counters()
        align = from_io.check_IO(verbose=False)
        if not align:
            continue
        else:
            from_io.manual_IO()

        # reset lc
        lc.reset(['lc-input','lc-ASIC','lc-emulator'])
        # configure acquire
        lc.configure_acquire(['lc-ASIC','lc-emulator'],"linkreset_ECONt")
        lc.do_capture(['lc-ASIC'])
        # send link reset econt
        fc.request("link_reset_econt")
        # check
        align = lc.check_links(['lc-ASIC'])
        data = lc.get_captured_data(['lc-ASIC'])
        # tv.save_testvector(f"asic_capture.csv",data['lc-ASIC'])
        if not align:
            continue
        else:
            break

    # find latency
    from latency import align
    lc_emu_aligned = align()

    # do compare
    x=call_i2c(args_name='FMTBUF_eporttx_numen',args_i2c="ASIC,emulator",args_write=False)
    num_links_asic = x['ASIC']['RW']['FMTBUF_ALL']['config_eporttx_numen']
    num_links_emu = x['emulator']['RW']['FMTBUF_ALL']['config_eporttx_numen']
    logging.debug(f"Num links {num_links_asic} {num_links_emu}")

    nwords = 4095
    lcaptures = ['lc-ASIC','lc-emulator']
    fc.configure_fc()
    lc.configure_acquire(lcaptures,'L1A',nwords,nwords,0)
    lc.do_capture(lcaptures)
    sc.configure_compare(13,trigger=True)
    err_counts = sc.reset_log_counters(0.01,verbose=False)

    if err_counts>0:
        logging.warning(f'eTx error count after alignment: {err_counts}')
        data = lc.get_captured_data(lcaptures,nwords)
        for lcapture in data.keys():
            tv.save_testvector(f"{lcapture}_compare_sc_align.csv",data[lcapture])
        exit()
    else:
        logging.info('Links are aligned between ASIC and emulator')
        
def bypass_align(idir="configs/test_vectors/alignment/",start_ASIC=0,start_emulator=13):
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
    logging.debug("New Latencies emu %s"%new_latencies)

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

    return err_counts
