import argparse
import os
import zmq_controller as zmqctrl

"""
PRBS tests.

To do the 28-bit PRBS tests, switch to the PRBS output and set up the headers.  
To do the 32-bit PRBS tests, just switch off the headers in elinkOutputs
"""

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Align links')
    parser.add_argument('--start-server', dest="start_server", type=bool, default=False, help='start servers directly in script (for debugging is better to do it separately)')
    args = parser.parse_args()

    server={'ASIC': '5554', 'emulator': '5555'}
    addr={'ASIC':0, 'emulator':1}

    env = os.environ.copy()
    from subprocess import PIPE, Popen
    cmds = {}
    cwds = {}
    for key in server.keys():
        cmds[key] = ['python3', '-u', 'zmq_server.py', '--addr', '%i'%(0x20+addr[key]), '--server', server[key]]
        cwds[key] = './zmq_i2c'

    # i2c for prbs
    prbs28_en = 1
    #prbs28_en = 0

    procs = {}
    if args.start_server:
        for key in server.keys():
            procs[key] = Popen(cmds[key], cwd=cwds[key],stdout=PIPE, universal_newlines=True, env=env)

    i2c_sockets = {}
    for key in server.keys():
        i2c_sockets[key] = zmqctrl.i2cController("localhost", str(server[key]), "configs/prbs.yaml")
        i2c_sockets[key].yamlConfig['ECON-T']['RW']['CH_ALIGNER_*INPUT_ALL']['registers']['config']['prbs28_en']['param_value'] = prbs28_en
        
        # arbitrarly change select (was 148)
        i2c_sockets[key].yamlConfig['ECON-T']['RW']['CH_ALIGNER_*INPUT_ALL']['registers']['sel_override_val'] = {'value': 200}
        print(i2c_sockets[key].yamlConfig)
        i2c_sockets[key].configure()

    # phase alignment for IO
    os.system('python testing/uhal-prbs.py')

    # read i2c registers (select and status)
    read_asic = i2c_sockets['ASIC'].read_config("configs/prbs.yaml","read")
    # print(read_asic)
    for i in range(12):
        print('Status prbs chck err %i'%i,hex(read_asic['RO']['CH_ALIGNER_%iINPUT_ALL'%i]['status_prbs_chk_err']))

    # terminate i2c servers
    for key,proc in procs.items():
        proc.terminate()
