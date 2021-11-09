import argparse
import os
import zmq_controller as zmqctrl
import logging
import numpy as np

logging.basicConfig()
logger = logging.getLogger("test-prbs")
logger.setLevel(logging.INFO)

"""
PRBS tests.

To do the 28-bit PRBS tests, switch to the PRBS output and set up the headers.  
To do the 32-bit PRBS tests, just switch off the headers in elinkOutputs
"""

def parse_prbs_registers(read):
    prbs_chck_err = [read['RO']['CH_ALIGNER_%iINPUT_ALL'%i]['status_prbs_chk_err'] for i in range(12)]
    hdr_mm_err = [read['RO']['CH_ALIGNER_%iINPUT_ALL'%i]['status_hdr_mm_err'] for i in range(12)]
    hdr_mm_cntr = [read['RO']['CH_ALIGNER_%iINPUT_ALL'%i]['hdr_mm_cntr'] for i in range(12)]
    orbsyn_fc_err_cnt = [read['RO']['CH_ALIGNER_%iINPUT_ALL'%i]['orbsyn_fc_err_cnt'] for i in range(12)]
    orbsyn_arr_err_cnt = [read['RO']['CH_ALIGNER_%iINPUT_ALL'%i]['orbsyn_arr_err_cnt'] for i in range(12)]
    orbsyn_hdr_err_cnt = [read['RO']['CH_ALIGNER_%iINPUT_ALL'%i]['orbsyn_hdr_err_cnt'] for i in range(12)]
    prbs_chk_err_cnt = [read['RO']['CH_ALIGNER_%iINPUT_ALL'%i]['prbs_chk_err_cnt'] for i in range(12)]
    with np.printoptions(formatter={'int':lambda x: f'{x:08x}'}, linewidth=120):
        for i in range(12):
            logger.info(f'Link {i:02d} prbs-chk-err 0x{prbs_chck_err[i]:02x}, header-mismatch 0x{hdr_mm_err[i]:02x}')
            logger.info(f'Counters: prbs-chk-err 0x{prbs_chk_err_cnt[i]:02x},  header-mismatch 0x{hdr_mm_cntr[i]:02x}, orbitsync-fc-err 0x{orbsyn_fc_err_cnt[i]:02x}, orbitsync-header-err 0x{orbsyn_hdr_err_cnt[i]:02x}, orbitsync-arrival-err 0x{orbsyn_arr_err_cnt[i]:02x}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test PRBS')
    parser.add_argument('--start-server', dest="start_server", action='store_true', default=False, help='start servers directly in script (for debugging is better to do it separately)')
    parser.add_argument('--select', dest="select", type=int, default=-1, help='modify alignment select value to test prbs errors')
    parser.add_argument('--prbs28', dest='prbs28',  action='store_true', default=False, help='PRBS 28 bit')
    args = parser.parse_args()

    #server={'ASIC': '5554', 'emulator': '5555'}
    server={'emulator': '5555'}
    #addr={'ASIC':0, 'emulator':1}
    addr={'emulator':1}

    env = os.environ.copy()
    from subprocess import PIPE, Popen
    cmds = {}
    cwds = {}
    for key in server.keys():
        cmds[key] = ['python3', '-u', 'zmq_server.py', '--addr', '%i'%(0x20+addr[key]), '--server', server[key]]
        cwds[key] = './zmq_i2c'

    procs = {}
    if args.start_server:
        for key in server.keys():
            procs[key] = Popen(cmds[key], cwd=cwds[key],stdout=PIPE, universal_newlines=True, env=env)

    i2c_sockets = {}
    for key in server.keys():
        i2c_sockets[key] = zmqctrl.i2cController("localhost", str(server[key]), "configs/prbs.yaml")
        if args.prbs28:
            i2c_sockets[key].yamlConfig['ECON-T']['RW']['CH_ALIGNER_*INPUT_ALL']['registers']['config']['prbs28_en'] = {'param_value': 1}
        else:
            i2c_sockets[key].yamlConfig['ECON-T']['RW']['CH_ALIGNER_*INPUT_ALL']['registers']['config']['prbs28_en'] = {'param_value': 0}
        i2c_sockets[key].configure()

        print('i2c settings for %s'%key)
        print('CH_ALIGNER_*INPUT_ALL: ', i2c_sockets[key].yamlConfig['ECON-T']['RW']['CH_ALIGNER_*INPUT_ALL'])
        i2c_sockets[key].configure()

    # read settings before sending PRBS
    read_asic = i2c_sockets['emulator'].read_config("configs/prbs.yaml","read")
    parse_prbs_registers(read_asic)
    
    # set prbs headers in elink-outputs (with uHal)
    if args.prbs28:
        print('Sending prbs 28 bit w elinkoutputs')
        os.system('python testing/uhal-prbs.py --prbs28')
    else:
        print('Sending prbs 32 bit w elinkoutputs')
        os.system('python testing/uhal-prbs.py')

    # read i2c registers (select and status)
    #read_asic = i2c_sockets['ASIC'].read_config("configs/prbs.yaml","read")
    read_asic = i2c_sockets['emulator'].read_config("configs/prbs.yaml","read")
    parse_prbs_registers(read_asic)

    # write select value
    if args.select!=-1:
        print('Setting select value to ',args.select)
        i2c_sockets[key].yamlConfig['ECON-T']['RW']['CH_ALIGNER_*INPUT_ALL']['registers']['config']['sel_override_en'] = {'param_value': 1}
        i2c_sockets[key].yamlConfig['ECON-T']['RW']['CH_ALIGNER_*INPUT_ALL']['registers']['sel_override_val'] = {'value': args.select}        

    # terminate i2c servers
    for key,proc in procs.items():
        proc.terminate()
