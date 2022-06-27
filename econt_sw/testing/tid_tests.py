from set_econt import *
from utils.asic_signals import ASICSignals
from i2c import call_i2c
from PRBS import scan_prbs
from delay_scan import delay_scan
import argparse,logging,os
import numpy as np
import pickle

def dump_i2c(tag='Initial'):
    logging.info(f"Reading all {tag} i2c settings")
    rw_status=call_i2c(args_name='RW')['ASIC']['RW']
    ro_status=call_i2c(args_name='RO')['ASIC']['RO']
    logging.debug(f'{tag} RO Status')
    logging.debug('%s'%ro_status)
    logging.debug(f'{tag} RW Status')
    logging.debug('%s'%rw_status)

def scan_PLL(odir,goodValue=27):
    logging.info(f"Scan over PLL VCOCapSelect value: PUSM_state, PLL_lfLocked")
    capSelectValues = np.array([  0,   1,   2,   3,   4,   5,   6,   7,   8,   9,  10,  11,  12,
                                  13,  14,  15,  24,  25,  26,  27,  28,  29,  30,  31,  56,  57,
                                  58,  59,  60,  61,  62,  63, 120, 121, 122, 123, 124, 125, 126,
                                  127, 248, 249, 250, 251, 252, 253, 254, 255, 504, 505, 506, 507,
                                  508, 509, 510, 511])
    states = {}
    for capSelect in capSelectValues:
        call_i2c(args_name='PLL_CBOvcoCapSelect',args_value=f'{capSelect}')
        status = call_i2c(args_name='PLL_lfLocked,PUSM_state')
        pusm_state = status['ASIC']['RO']['MISC_ALL']['misc_ro_0_PUSM_state']
        pll_locked = status['ASIC']['RO']['PLL_ALL']['pll_read_bytes_2to0_lfLocked']
        states[capSelect] = [pusm_state, pll_locked]
        logging.info(f"PLL VCOCapSelect {capSelect}: {pusm_state}  {pll_locked}")
    
    call_i2c(args_name='PLL_CBOvcoCapSelect',args_value=f'{goodValue}')

    with open(f'{odir}/pll_vcocapselect_scan.pkl','wb') as f:
        pickle.dump(states,f)
        
def TID_check(board,odir,voltage):
    logging.info(f"TID tests with voltage {voltage} and output directory {odir}")

    # Read all i2c settings
    dump_i2c('Initial')

    # Do a hard reset
    logging.info(f"Hard reset")
    resets = ASICSignals()
    resets.send_reset(reset='hard',i2c='ASIC')
    resets.send_reset(reset='hard',i2c='emulator')

    # Read all i2c settings after hard reset
    dump_i2c('After Hard Reset')

    dirs = [
        "configs/test_vectors/mcDataset/STC_type0_eTx1/",
    ]
    os.system(f'mkdir -p {odir}')
    
    # Initialize
    startup()
    
    # PLL VCO Cap select scan and set value back
    scan_PLL(odir,goodValue=27)
    
    # PRBS phase scan
    logging.info(f"Scan phase w PRBS err counters")
    err_counts, best_setting = scan_prbs(32,'ASIC',1,range(0,12),True,False)
    logging.debug("Error counts %s"%err_counts)
    with open(f'{odir}/prbs_scan.pkl', 'wb') as f:
        pickle.dump(err_counts,f)
        
    # Other init steps
    set_phase(board) # set phase w board settings
    set_phase_of_enable(0)
    set_runbit()
    read_status()
    dump_i2c('After configuration')
    
    # Input word alignment
    set_fpga()
    word_align(bx=None,emulator_delay=None)
    
    # Output alignment
    io_align()
    output_align()
    
    # Bypass alignment
    bypass_align(idir="configs/test_vectors/alignment/",start_ASIC=0,start_emulator=1)
    
    # Compare for various configurations
    for idir in dirs:
        bypass_compare(idir)
    
    # Scan IO delay
    delay_scan(odir,io='from')
    io_align()
    
    # Soft reset
    logging.info(f"Soft reset")
    resets.send_reset(reset='soft',i2c='ASIC')
    resets.send_reset(reset='soft',i2c='emulator')
    dump_i2c('After Soft Reset')
    
    logging.info(f"Finalized test")

if __name__ == "__main__":
    """
    Test ECON-T functionality after time in beam
    """

    parser = argparse.ArgumentParser()
    parser.add_argument('--board','-b', default=12, type=int, help='Board number')
    parser.add_argument('--odir', type=str, default='test', help='output dir')
    parser.add_argument('--voltage', type=float, default=1.2, help='voltage')
    parser.add_argument('--logName', default='logFile.log', help='log name')
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)-6s %(message)s',
                        datefmt='%H:%M:%S',
                        filename=args.logName,
                        filemode='a')

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)-6s %(message)s',datefmt='%H:%M:%S')
    console.setFormatter(formatter)
    logging.getLogger().addHandler(console)

    TID_check(args.board,args.odir,args.voltage)
