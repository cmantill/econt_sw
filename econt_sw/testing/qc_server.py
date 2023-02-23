from set_econt import startup,set_phase,set_phase_of_enable,set_runbit,read_status,set_fpga,word_align,output_align,bypass_align,bypass_compare
from utils.asic_signals import ASICSignals
from i2c import I2C_Client
from PRBS import scan_prbs
from PLL import scanCapSelect
from delay_scan import delay_scan
from TestStand_Controls import psControl
import csv
import argparse,os,pickle,pprint
import numpy as np
import sys,copy
import logging
import datetime
import sqlite3
import numpy as np
import socket
import os, time, datetime
board = 46
i2cClient=I2C_Client(forceLocal=True)

def consecutive(data, stepsize=1):
    return np.split(data, np.where(np.diff(data) != stepsize)[0]+1)

def get_max_width(err_counts, channels, padding): # channels 12 for phase scan and 13 for io_scan || padding 4
    max_width_by_ch = []
    second_max_width_by_ch = []
    err_wrapped=np.concatenate([err_counts,err_counts[:padding]])
    for ch in range(channels):
        if channels == 13:
            x = err_wrapped[ch,:]
        else:
            x = err_wrapped[:,ch]
        phases = consecutive(np.argwhere(x==0).flatten())
        sizes = [np.size(a) for a in phases]
        max_width = max(sizes)
        sizes.remove(max_width)
        try:
            second_max_width = max(sizes)
        except:
            second_max_width = 0
        max_width_by_ch.append(max_width)
        second_max_width_by_ch.append(second_max_width)
    return max_width_by_ch, second_max_width_by_ch

def qc_i2c(i2c_address=0x20):
    rw_test = False
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
        rw_one_test = True
        rw_zero_test = True
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

        no_match_one = is_match(pairs_one,pairs_one_read)
        if no_match_one:
            rw_one_test = False
            logging.warning("Read one pairs do not match %s",no_match_one)
            np.savetxt(f"{odir}/rw_pair_one_comparion_{tag}.txt", np.array([pairs_one, pairs_one_read]), delimiter=' ', fmt='%s', header='')
        logging.info(f"Writing zeros to all registers")
        board.write_pairs(pairs_zero)
        pairs_zero_read = board.read_pairs(pairs_zero)

        no_match_zero = is_match(pairs_zero,pairs_zero_read)
        if no_match_zero:
            rw_zero_test = False
            logging.warning("Read zero pairs do not match %s",no_match_zero)
            np.savetxt(f"{odir}/rw_pair_zero_comparion_{tag}.txt", np.array([pairs_zero, pairs_zero_read]), delimiter=' ', fmt='%s', header='')
        return rw_one_test, rw_zero_test

    from econ_interface import econ_interface
    board = econ_interface(i2c_address, 1, fpath="zmq_i2c/")
    rw_one, rw_zero = ping_all_addresses()
    if (rw_one and rw_zero):
        rw_test = True
        logging.info(f"Read Write test passed")
    else:
        logging.warning("Read Write test failed")
    return rw_test

def econt_qc(board,odir,tag,good_capSelect_Value=27,thresold_max_width=4,thresold_second_max_width=3,max_IO_delay_scan_width_thresold = 14, second_max_IO_delay_scan_width_thresold = 13):
     #date and time
    start_ = datetime.datetime.now()
    test_start_time  = start_.strftime("%Y-%m-%d_%H:%M:%S")

    logging.info(f"---------------------------------Test Begain--------------------------------")
    logging.info(f"All test data  file are stored in output directory {odir}/chip_{chip}")

    # power voltage and current to chip test
    powerControl = psControl(host="192.168.206.50")
    real_voltage = powerControl.Read_Power(board=board)
    np.savetxt(f"{odir}/power_voltage_current_{tag}.txt", np.array([real_voltage]), delimiter=" ", fmt="%s", header="")
    logging.info(f"power, voltage and current  to chip : {real_voltage[0]},  {real_voltage[1]}, {real_voltage[2]}")

    # Stress test i2c
    rw_test = qc_i2c()

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

    #TODO: find good value automatically
    VCOCapSelected = scanCapSelect(verbose=True, odir=odir, tag=tag)
    pll_test = False
    if len(VCOCapSelected)!=0:
        logging.info(f"Good PLL VCOCapSelect values: %s"%VCOCapSelected)
        np.savetxt(f"{odir}/good_capSelected_values_{tag}.txt", np.array([VCOCapSelected]), delimiter=" ", fmt="%d", header="")
        pll_test = True
    else:
        logging.info("No Good PLL VCOCapSelect values")

    logging.debug(f"Setting VCOCapSelect value to {good_capSelect_Value}")
    i2cClient.call(args_name='PLL_CBOvcoCapSelect',args_value=f'{good_capSelect_Value}')

    # PRBS phase scan, max and second max phase width, phase_width_test
    phase_width_test=False
    logging.info(f"Scan phase w PRBS err counters and width")
    err_counts, best_setting = scan_prbs(32,'ASIC',0.05,range(0,12),True,verbose=False,odir=odir,tag=tag)
    np.savetxt(f"{odir}/best_phase_scan_seting_{tag}.txt", np.array([best_setting]), delimiter=" ", fmt="%d", header="")
    logging.info(f"Best phase settings found to be {str(best_setting)}")
    max_width, second_max_width =  get_max_width(err_counts, channels=12, padding=4)
    np.savetxt(f"{odir}/width_of_phase_scan_seting_{tag}.txt", np.array([max_width, second_max_width]), delimiter=" ", fmt="%d", header="")
    logging.info(f" Max width of good phase settings {max_width}")
    logging.info(f" Second Max width of good phase settings {second_max_width}")
    width1 = np.array([thresold_max_width] * 12)
    width2 = np.array([thresold_second_max_width] * 12)
    np.savetxt(f"{odir}/phase_width_comparion_{tag}.txt", np.array([max_width >= width1, second_max_width >= width2]), delimiter=' ', fmt='%d', header='')
    if ((max_width >= width1).all() and (second_max_width >= width2).all()):
        phase_width_test = True
        logging.info(f"passed phase width test")
    else:

        logging.info(f"failed phase width test")

    # Other init steps
    set_phase(best_setting=','.join([str(i) for i in best_setting]))
    set_phase_of_enable(0)
    set_runbit(1)
    read_status()

    # Input word alignment
    logging.info("Align input words")
    set_fpga()
    # try:
    word_align(bx=None,emulator_delay=None)
    # except ERROR:
    #     pass

    # Scan IO delay scan and width and io_delay_scan_test
    io_scan_test = False
    logging.info('from IO delay scan')
    set_runbit(0)
    i2cClient.call(args_yaml="configs/alignOutput_TS.yaml",args_i2c='ASIC,emulator',args_write=True)
    set_runbit(1)
    logging.debug(f"Configured ASIC/emulator with all eTx")
    errorcounts = delay_scan(odir,ioType='from',tag=tag)
    err_counts_io = list(errorcounts.values())
    logging.debug("Error counts form IO delay scan: %s"%err_counts_io)
    max_width_io, second_max_width_io =  get_max_width(err_counts_io, channels=13, padding=10)
    np.savetxt(f"{odir}/width_of_io_scan_seting_{tag}.txt", np.array([max_width_io, second_max_width_io]), delimiter=" ", fmt="%d", header="")
    logging.info(f" Max width of io-scan settings {max_width_io}")
    logging.info(f" Second Max width of io-scan settings {second_max_width_io}")
    max_IO_delay = np.array([max_IO_delay_scan_width_thresold] * 13)
    second_max_IO_delay = np.array([second_max_IO_delay_scan_width_thresold] * 13)
    np.savetxt(f"{odir}/io_delay_width_comparion_{tag}.txt", np.array([max_width_io >= max_IO_delay,second_max_width_io >= second_max_IO_delay]), delimiter=" ", fmt="%d", header="")
    if ((max_width_io >= max_IO_delay).all() and (second_max_width_io >= second_max_IO_delay).all()):
        io_scan_test = True
        logging.info(f"passed io scan delay width test")
    else:
        logging.info(f"failed io scan delay width test")



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
        i2cClient.call(args_name='EPRXGRP_TOP_trackMode', args_value=f'{trackmode}')
        phaseSelect_vals = []
        for trainchannel in range(0, 50):
            i2cClient.call(args_name='CH_EPRXGRP_*_trainChannel', args_value='1')
            i2cClient.call(args_name='CH_EPRXGRP_*_trainChannel', args_value='0')
            x = i2cClient.call(args_name='CH_EPRXGRP_*_status_phaseSelect',args_i2c='ASIC')
            phaseSelect_vals.append([x['ASIC']['RO'][f'CH_EPRXGRP_{channel}INPUT_ALL']['status_phaseSelect'] for channel in range(0, 12)])

        with open(f'{odir}/trackmode{trackmode}_phaseSelect{tag}.csv', 'w') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerows(zip(*phaseSelect_vals))

    # Soft reset
    logging.info(f"Soft reset")
    resets.send_reset(reset='soft',i2c='ASIC')
    resets.send_reset(reset='soft',i2c='emulator')
    logging.info(f"Read Write Test --->  {rw_test}")
    logging.info(f"PLL Test --->  {pll_test}")
    logging.info(f"Phase Width Test --->   {phase_width_test}")
    logging.info(f"IO Phase Width Test --->  {io_scan_test}")
    over_all_test = False
    if(rw_test and pll_test and phase_width_test and io_scan_test):
        over_all_test = True
        logging.info("----------->pass all the tests<----------------")
    else:
        logging.info("!!!!!!!!!!failed to pass all tests!!!!!!!!!!!!!!!!!!")
    end_ = datetime.datetime.now()
    test_end_time  = end_.strftime("%Y-%m-%d_%H:%M:%S")
    logging.info(f"---------------------------------Finalized test-------------------------------")
    return  real_voltage[1], over_all_test, rw_test, pll_test, phase_width_test, io_scan_test, 1

# #==================================================================================

odir = f"data"
# IP = "192.168.1.48"
IP = "127.0.0.1"
PORT = 9999
SIZE = 10240
FORMAT = "utf-8"
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print("socket created")
server.bind((IP,PORT))
server.listen()
print("server started")
print("Waiting fom request from client")
# SERVER_FOLDER = "/home/HGCAL_dev/bbbam/econt_sw/econt_sw/data"
while True:

    conn, addr = server.accept()


    msg = conn.recv(SIZE).decode()
    message, chip_,thresold_max_width_,thresold_second_max_width_, max_IO_delay_scan_width_thresold_, second_max_IO_delay_scan_width_thresold_ = msg.split('|')
    chip = int(chip_)
    x1 = int(thresold_max_width_)
    x2 = int(thresold_second_max_width_)
    x3 = int(max_IO_delay_scan_width_thresold_)
    x4 = int(second_max_IO_delay_scan_width_thresold_)

    print(f"Received request from client: {message} for chip_{chip}")
    if message == 'start':
        if os.path.exists(f'{odir}'):
            os.system(f'rm -r {odir}')
        os.system(f'mkdir -p {odir}')
        tag=f"chip_{chip}"


        # os.system(f'mkdir -p {odir}')


        logName=f"{odir}/logFile_{tag}.log"
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s - {_tag} - %(levelname)-6s %(message)s'.format(_tag=tag),
                            datefmt='%m-%d-%y %H:%M:%S',
                            filename=logName,
                            filemode='a')
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        _f='%(asctime)s - {_tag} - %(levelname)-6s %(message)s'.format(_tag=tag)
        console.setFormatter(logging.Formatter(_f))
        logging.getLogger().addHandler(console)


        real_voltage, over_all_test, rw_test, pll_test, phase_width_test, io_scan_test,test_ended = econt_qc(board, odir, tag, 27, x1, x2, x3, x4)
        # path = os.path.join(SERVER_FOLDER)
        # files = os.listdir(path)
        conn.send(bytes(f"{real_voltage}|{over_all_test}|{rw_test}|{pll_test}|{phase_width_test}|{io_scan_test}|{test_ended}",f"{FORMAT}"))
        logging.getLogger().handlers.clear()
        conn.close()
        # time.sleep(2)
        # real_voltage, over_all_test, rw_test, pll_test, phase_width_test, io_scan_test = 1,1,1,1,1,1
#==================================================================================
