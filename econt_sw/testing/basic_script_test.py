from set_econt import startup,set_phase,set_phase_of_enable,set_runbit,read_status,set_fpga,word_align,io_align,output_align,bypass_align,bypass_compare
from utils.asic_signals import ASICSignals
from i2c import call_i2c
from PRBS import scan_prbs
from PLL import scanCapSelect
from delay_scan import delay_scan

import argparse,os,pickle,pprint
import numpy as np

#def dump_i2c(tag='Initial',odir='logs'):
#    logging.info(f"Reading all {tag} i2c settings")
#    rw_status=call_i2c(args_name='RW')['ASIC']['RW']
#    ro_status=call_i2c(args_name='RO')['ASIC']['RO']

#    with open(f'{odir}/I2C_Status_{tag}.log','w') as _file:
#        _file.write(pprint.pformat(rw_status))
#        _file.write(pprint.pformat(ro_status))
#
#    logging.debug(f'{tag} RO Status')
#    logging.debug('%s'%ro_status)
#    logging.debug(f'{tag} RW Status')
#    logging.debug('%s'%rw_status)
        
def TID_check(board,odir,voltage,tag=''):

    logging.info(f"TID tests with voltage {voltage} and output directory {odir}")

    # Read all i2c settings
#    dump_i2c(f'Initial{tag}',odir)
    
    # Do a hard reset
    logging.info(f"Hard reset")
    resets = ASICSignals()
    resets.send_reset(reset='hard',i2c='ASIC')
    resets.send_reset(reset='hard',i2c='emulator')

    # Read all i2c settings after hard reset
#    dump_i2c(f'AfterHardReset{tag}',odir)

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
    os.system(f'mkdir -p {odir}')
    
    # Initialize
    startup()
    
    # PLL VCO Cap select scan and set value back
#    logging.info(f"Scan over PLL VCOCapSelect values")
#    goodValue = 27
#    goodValues = scanCapSelect(verbose=True)
#    logging.info(f"Good PLL VCOCapSelect values: %s"%goodValues)
#    call_i2c(args_name='PLL_CBOvcoCapSelect',args_value=f'{goodValue}')
    
    # PRBS phase scan
    logging.info(f"Scan phase w PRBS err counters")
    err_counts, best_setting = scan_prbs(32,'ASIC',0.05,range(0,12),True,verbose=False,odir=odir,tag=tag)

    logging.info(f"Best phase settings found to be {str(best_setting)}")
    # Other init steps
    set_phase(best_setting=','.join([str(i) for i in best_setting]))
    set_phase_of_enable(0)
    set_runbit()
    read_status()
#    dump_i2c(f'AfterConfig{tag}',odir)
    
    # Input word alignment
    set_fpga()
    word_align(bx=None,emulator_delay=None)
    
    # Output alignment
    io_align()
    output_align(verbose=False)
    
    # Bypass alignment
    bypass_align(idir="configs/test_vectors/alignment/",start_ASIC=0,start_emulator=1)

    # Compare for various configurations
    for idir in dirs:
        bypass_compare(idir,odir)

    logging.info('Starting delay scan')
    # Scan IO delay
    err_counts = delay_scan(odir,ioType='from',tag=tag)
    logging.debug("Error counts form IO delay scan: %s"%err_counts)   

    # Compare I2C again
    dump_i2c(f'AfterTests{tag}',odir)

    # Soft reset
    logging.info(f"Soft reset")
    resets.send_reset(reset='soft',i2c='ASIC')
    resets.send_reset(reset='soft',i2c='emulator')
#    dump_i2c(f'AfterSoftReset{tag}',odir)
    
    logging.info(f"Finalized test")

if __name__ == "__main__":
    """
    Test ECON-T functionality after time in beam
    """

    parser = argparse.ArgumentParser()
    parser.add_argument('--board','-b', default=12, type=int, help='Board number')
    parser.add_argument('--odir', type=str, default='test', help='output dir')
    parser.add_argument('--voltage', type=float, default=1.2, help='voltage')
    parser.add_argument('--tag', default=None, help='tag for extra logs')
    args = parser.parse_args()

    if args.tag is None:
        _tag='_{args.voltage}V'
    else:
        _tag=f"_{args.voltage}V_{args.tag}"

    os.system(f'mkdir -p {args.odir}')

    logName=f"{args.odir}/logFile{_tag}.log"
    voltage_str = f"Voltage {args.voltage}"
    import logging
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - {_voltage} - %(levelname)-6s %(message)s'.format(_voltage=voltage_str),
                        datefmt='%m-%d-%y %H:%M:%S',
                        filename=logName,
                        filemode='a')
                    #     handlers=[
                    #         logging.FileHandler(logName),
                    #         logging.StreamHandler()
                    #     ]
                    # )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    _f='%(asctime)s - {_voltage} - %(levelname)-6s %(message)s'.format(_voltage=voltage_str)
    console.setFormatter(logging.Formatter(_f))
    logging.getLogger().addHandler(console)

    TID_check(args.board,args.odir,args.voltage,_tag)

print(bypass_compare(idir,odir))
