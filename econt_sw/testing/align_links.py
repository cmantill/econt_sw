import argparse
import os
import zmq_controller as zmqctrl

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

    # i2c for alignment
    orbsyn_cnt_snapshot = 7
    match_pattern_val = 0x9cccccccaccccccc

    procs = {}
    if args.start_server:
        for key in server.keys():
            procs[key] = Popen(cmds[key], cwd=cwds[key],stdout=PIPE, universal_newlines=True, env=env)

    i2c_sockets = {}
    for key in server.keys():
        i2c_sockets[key] = zmqctrl.i2cController("localhost", str(server[key]), "configs/align.yaml")
        i2c_sockets[key].yamlConfig['ECON-T']['RW']['ALIGNER_ALL']['registers']['orbsyn_cnt_snapshot']['value'] = orbsyn_cnt_snapshot
        i2c_sockets[key].yamlConfig['ECON-T']['RW']['ALIGNER_ALL']['registers']['match_pattern_val']['value'] = match_pattern_val
        i2c_sockets[key].configure()

        # read back i2c 
        read_socket = i2c_sockets[key].read_config("configs/align.yaml")
        print('TX sync word %s '%key,hex(read_socket['RW']['FMTBUF_ALL']['tx_sync_word']))

    # phase alignment for IO
    os.system('python testing/uhal-align_on_tester.py --step tester-phase')
    os.system('python testing/uhal-align_on_tester.py --step asic-word')

    # read i2c registers (select and status)
    read_asic = i2c_sockets['ASIC'].read_config("configs/align.yaml","read")
    print(read_asic)
    for i in range(12):
        # status should be 0x3
        # alignment patern should be in snapshot
        print('Status link %i'%i,hex(read_asic['RO']['CH_ALIGNER_%iINPUT_ALL'%i]['status']))
        print('Snapshot link %i'%i,hex(read_asic['RO']['CH_ALIGNER_%iINPUT_ALL'%i]['snapshot']))

    # relative alignment for IO
    os.system('python testing/uhal-align_on_tester.py --step asic-tester')

    # terminate i2c servers
    for key,proc in procs.items():
        proc.terminate()
