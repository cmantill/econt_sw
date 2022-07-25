from set_econt import startup,set_phase,set_phase_of_enable,set_runbit,read_status,set_fpga,word_align,io_align,output_align,bypass_align,bypass_compare
from utils.asic_signals import ASICSignals
from i2c import call_i2c
from PRBS import scan_prbs
from PLL import scanCapSelect
from delay_scan import delay_scan

import argparse,os,pickle,pprint
import numpy as np
        
def econt_check(board,odir,voltage,tag=''):

    logging.info(f"Tests with voltage {voltage} and output directory {odir}, board {board}.")
    
    # Do a hard reset
    logging.info(f"Hard reset")
    resets = ASICSignals()
    resets.send_reset(reset='hard',i2c='ASIC')
    resets.send_reset(reset='hard',i2c='emulator')

    dirs = [
        "configs/test_vectors/mcDataset/STC_type0_eTx5/",
        "configs/test_vectors/mcDataset/STC_type1_eTx2/",
        "configs/test_vectors/mcDataset/STC_type2_eTx3/",
        "configs/test_vectors/mcDataset/STC_type3_eTx4/",
        "configs/test_vectors/mcDataset/RPT_13eTx/",
        "configs/test_vectors/mcDataset/TS_Thr47_13eTx/",
        "configs/test_vectors/mcDataset/BC_12eTx/",
        "configs/test_vectors/mcDataset/BC_1eTx/",
    ]
    
    # Initialize
    logging.info("Initializing")
    startup()
    
    # PLL VCO Cap select scan and set value back
    logging.info(f"Scan over PLL VCOCapSelect values")
    goodValue = 27
    #TO DO: find good value automatically 
    goodValues = scanCapSelect(verbose=True, odir=odir,tag=tag)
    logging.info(f"Good PLL VCOCapSelect values: %s"%goodValues)
    call_i2c(args_name='PLL_CBOvcoCapSelect',args_value=f'{goodValue}')
    
    # PRBS phase scan
    logging.info(f"Scan phase w PRBS err counters")
    err_counts, best_setting = scan_prbs(32,'ASIC',0.05,range(0,12),True,verbose=False,odir=odir,tag=tag)

    logging.info(f"Best phase settings found to be {str(best_setting)}")
    # Other init steps
    set_phase(best_setting=','.join([str(i) for i in best_setting]))
    set_phase_of_enable(0)
    set_runbit()
    read_status()
    
    # Input word alignment
    logging.info("Inputting word alignment")
    set_fpga()
    word_align(bx=None,emulator_delay=None)
    
    # Output alignment
    logging.info("Outputting word alignment")
    io_align()
    output_align(verbose=False)
    
    # Bypass alignment
    logging.info("Bypassing alignment")
    bypass_align(idir="configs/test_vectors/alignment/",start_ASIC=0,start_emulator=12)

    # Compare for various configurations
    logging.info("Comparing various configurations")
    for idir in dirs:
        bypass_compare(idir,odir)

    logging.info('Starting delay scan')
    # Scan IO delay
    err_counts = delay_scan(odir,ioType='from',tag=tag)
    logging.debug("Error counts form IO delay scan: %s"%err_counts)   

    # Soft reset
    logging.info(f"Soft reset")
#    resets.send_reset(reset='soft',i2c='ASIC')
 #   resets.send_reset(reset='soft',i2c='emulator')
    
    logging.info(f"Finalized test")

if __name__ == "__main__":
    """
    Test ECON-T functionality 
    """

    parser = argparse.ArgumentParser()
    parser.add_argument('--board','-b', default=12, type=int, help='Board number')
    parser.add_argument('--odir', type=str, default='packaged_results', help='output dir')
    parser.add_argument('--voltage', type=float, default=1.2, help='voltage')
    parser.add_argument('--tag', default=None, help='tag for extra logs')
    args = parser.parse_args()

    if args.tag is None:
        _tag=f'_{args.voltage}V_{args.board}board'
    else:
        _tag=f"_{args.voltage}V_{args.tag}_{args.board}board"

    os.system(f'mkdir -p {args.odir}')

    logName=f"{args.odir}/logFile{_tag}.log"
    voltage_str = f"Voltage {args.voltage}"
    import logging
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - {_voltage} - %(levelname)-6s %(message)s'.format(_voltage=voltage_str),
                        datefmt='%m-%d-%y %H:%M:%S',
                        filename=logName,
                        filemode='a')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    _f='%(asctime)s - {_voltage} - %(levelname)-6s %(message)s'.format(_voltage=voltage_str)
    console.setFormatter(logging.Formatter(_f))
    logging.getLogger().addHandler(console)

    econt_check(args.board,args.odir,args.voltage,_tag)
