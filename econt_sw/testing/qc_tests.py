from set_econt import startup,set_phase,set_phase_of_enable,set_runbit,read_status,set_fpga,word_align,output_align,bypass_align,bypass_compare
from utils.asic_signals import ASICSignals
from i2c import call_i2c
from PRBS import scan_prbs
from PLL import scanCapSelect
from delay_scan import delay_scan

import csv
import argparse,os,pickle,pprint
import numpy as np
import sys,copy

def qc_i2c(i2c_address=0x20):
    sys.path.append( 'zmq_i2c/')

    def is_match(pairs,pairs_read):
        no_match = {}
        for key, value in pairs.items():
            register_value = int.from_bytes(value[0], 'little')
            if key in pairs_read.keys():
                size_byte = value[1]
                if isinstance(pairs_read[key][0], list):
                    read_value = int.from_bytes(pairs_read[key][0], 'little')
                else:
                    read_value = pairs_read[key][0]
            if read_value != register_value:
                no_match[key] = read_value
        return no_match

    def ping_all_addresses():
        default_pairs = board.translator.pairs_from_cfg(allowed=['RW'])
        
        pairs_one = copy.deepcopy(default_pairs)
        pairs_zero = copy.deepcopy(default_pairs)

        for key, value in pairs_one.items():
            size_byte = value[1]
            pairs_one[key][0] = int("1"*8*size_byte,2).to_bytes(size_byte,'little')
            pairs_zero[key][0] = int("0").to_bytes(size_byte,'little')

        #DO NOT TURN OFF ERX_MUX_1                                                                                                                                                             
        # This is the FCMD_CLK input, disabling it disables i2c clock                                                                                                                          
        pairs_zero[1267][0]=b'\x01'

        logging.info(f"Writing ones to all registers")
        board.write_pairs(pairs_one)
        pairs_one_read = board.read_pairs(pairs_one) 
        no_match = is_match(pairs_one,pairs_one_read)
        if no_match:
            logging.warning("Read pairs do not match %s",no_match)

        logging.info(f"Writing zeros to all registers")
        board.write_pairs(pairs_zero)
        pairs_zero_read = board.read_pairs(pairs_zero)
        no_match = is_match(pairs_zero,pairs_zero_read)
        if no_match:
            logging.warning("Read pairs do not match %s",no_match)

    from econ_interface import econ_interface
    board = econ_interface(i2c_address, 1, fpath="zmq_i2c/")
    ping_all_addresses()

def econt_qc(board,odir,voltage,tag=''):

    logging.info(f"Tests with voltage {voltage} and output directory {odir}, board {board}.")

    # Stress test i2c
    qc_i2c()

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
        "configs/test_vectors/mcDataset/TS_Thr47_12eTx/",
        "configs/test_vectors/mcDataset/TS_Thr47_11eTx/",
        "configs/test_vectors/mcDataset/TS_Thr47_10eTx/",
        "configs/test_vectors/mcDataset/TS_Thr47_9eTx/",
        "configs/test_vectors/mcDataset/TS_Thr47_8eTx/",
        "configs/test_vectors/mcDataset/TS_Thr47_7eTx/",
        "configs/test_vectors/mcDataset/TS_Thr47_6eTx/",
        "configs/test_vectors/mcDataset/TS_Thr47_5eTx/",
        "configs/test_vectors/mcDataset/TS_Thr47_4eTx/",
        "configs/test_vectors/mcDataset/TS_Thr47_3eTx/",
        "configs/test_vectors/mcDataset/TS_Thr47_2eTx/",
        "configs/test_vectors/mcDataset/TS_Thr47_1eTx/",
        "configs/test_vectors/mcDataset/BC_12eTx/",
        "configs/test_vectors/mcDataset/BC_1eTx/",
    ]
    
    # Initialize
    logging.info("Initializing")
    startup()
    
    # PLL VCO Cap select scan and set value back
    logging.info(f"Scan over PLL VCOCapSelect values")
    goodValue = 27
    #TODO: find good value automatically 
    goodValues = scanCapSelect(verbose=True, odir=odir,tag=tag)
    logging.info(f"Good PLL VCOCapSelect values: %s"%goodValues)
    logging.debug(f"Setting VCOCapSelect value to {goodValue}")
    call_i2c(args_name='PLL_CBOvcoCapSelect',args_value=f'{goodValue}')
    
    # PRBS phase scan
    logging.info(f"Scan phase w PRBS err counters")
    err_counts, best_setting = scan_prbs(32,'ASIC',0.05,range(0,12),True,verbose=False,odir=odir,tag=tag)
    logging.info(f"Best phase settings found to be {str(best_setting)}")

    # Other init steps
    set_phase(best_setting=','.join([str(i) for i in best_setting]))
    set_phase_of_enable(0)
    set_runbit(1)
    read_status()

    # Input word alignment
    logging.info("Align input words")
    set_fpga()
    word_align(bx=None,emulator_delay=None)
    
    # Scan IO delay scan
    logging.info('from IO delay scan')
    set_runbit(0)
    call_i2c(args_yaml="configs/alignOutput_TS.yaml",args_i2c='ASIC,emulator',args_write=True)
    set_runbit(1)
    logging.debug(f"Configured ASIC/emulator with all eTx")
    err_counts = delay_scan(odir,ioType='from',tag=tag)
    logging.debug("Error counts form IO delay scan: %s"%err_counts)

    # Output alignment
    logging.info("Outputting word alignment")
    output_align(verbose=False)
        
    # Bypass alignment
    logging.info("Bypassing alignment")
    bypass_align(idir="configs/test_vectors/alignment/",start_ASIC=0,start_emulator=13)

    # Compare for various configurations
    logging.info("Comparing various configurations")
    dict = {}
    for idir in dirs:
        dict[idir] = bypass_compare(idir, odir)
    with open(f'{odir}/error_counts_{tag}.csv', 'w') as csvfile:
        for key in dict.keys():
            csvfile.write("%s, %s\n"%(key, dict[key]))

    # Test the different track modes and train channels   
    logging.info('Testing track modes')
    for trackmode in range(1, 4):
        call_i2c(args_name='EPRXGRP_TOP_trackMode', args_value=f'{trackmode}')
        phaseSelect_vals = []
        for trainchannel in range(0, 50):
            call_i2c(args_name='CH_EPRXGRP_*_trainChannel', args_value='1')
            call_i2c(args_name='CH_EPRXGRP_*_trainChannel', args_value='0')
            x = call_i2c(args_name='CH_EPRXGRP_*_status_phaseSelect',args_i2c='ASIC')
            phaseSelect_vals.append([x['ASIC']['RO'][f'CH_EPRXGRP_{channel}INPUT_ALL']['status_phaseSelect'] for channel in range(0, 12)])

        with open(f'{odir}/trackmode{trackmode}_phaseSelect_{board}board.csv', 'w') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(zip(*phaseSelect_vals))

    # Soft reset
    logging.info(f"Soft reset")
    resets.send_reset(reset='soft',i2c='ASIC')
    resets.send_reset(reset='soft',i2c='emulator')
    
    logging.info(f"Finalized test")

if __name__ == "__main__":
    """
    Test ECON-T functionality 
    """

    parser = argparse.ArgumentParser()
    parser.add_argument('--board','-b', required=True, help='Board number')
    parser.add_argument('--odir', type=str, default='qc_results_08_22', help='output dir')
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

    econt_qc(args.board,args.odir,args.voltage,_tag)
