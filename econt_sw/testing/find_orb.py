import argparse
import os
import zmq_controller as zmqctrl

"""
To be run after IO blocks are aligned.
"""

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Align links')
    parser.add_argument('--start-server', dest="start_server", action='store_true', default=False, help='start servers directly in script (for debugging is better to do it separately)')
    parser.add_argument('--delay', type=int, default=4, help="delay")
    parser.add_argument('--snap', dest="snap", default=[3,3], nargs="+", help="orbsyn cnt snapshot for [ASIC,emulator]")
    parser.add_argument('--val', dest="val", default=[0,0], nargs="+", help="orbsyn cnt val for [ASIC,emulator]")
    args = parser.parse_args()
    print(args)

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
    orbsyn_cnt_snapshot = {
        'ASIC': int(args.snap[0]),
        'emulator': int(args.snap[1]),
    }
    orbsyn_cnt_load_val = {
        'ASIC': int(args.val[0]),
        'emulator': int(args.val[1])
    }
    match_pattern_val = 0x9cccccccaccccccc

    procs = {}
    if args.start_server:
        for key in server.keys():
            procs[key] = Popen(cmds[key], cwd=cwds[key],stdout=PIPE, universal_newlines=True, env=env)

    i2c_sockets = {}
    for key in server.keys():
        i2c_sockets[key] = zmqctrl.i2cController("localhost", str(server[key]), "configs/align.yaml")
        i2c_sockets[key].yamlConfig['ECON-T']['RW']['ALIGNER_ALL']['registers']['orbsyn_cnt_load_val']['value'] = orbsyn_cnt_load_val[key]
        i2c_sockets[key].yamlConfig['ECON-T']['RW']['ALIGNER_ALL']['registers']['orbsyn_cnt_snapshot']['value'] = orbsyn_cnt_snapshot[key]
        i2c_sockets[key].yamlConfig['ECON-T']['RW']['ALIGNER_ALL']['registers']['match_pattern_val']['value'] = match_pattern_val
        i2c_sockets[key].configure()

        # read back i2c 
        read_socket = i2c_sockets[key].read_config("configs/align.yaml")
        print('TX sync word %s '%key,hex(read_socket['RW']['FMTBUF_ALL']['tx_sync_word']))

        # findorb
        os.system('python testing/uhal-findorb.py --delay %i'%args.delay)

    # read i2c registers (select and status)
    read_emulator = i2c_sockets['emulator'].read_config("configs/align.yaml","read")
    read_asic = i2c_sockets['ASIC'].read_config("configs/align.yaml","read")

    orbsyn_cnt_snapshot_asic = read_asic['RW']['ALIGNER_ALL']['orbsyn_cnt_snapshot']
    orbsyn_cnt_snapshot_emu = read_emulator['RW']['ALIGNER_ALL']['orbsyn_cnt_snapshot']
    print('Orbit cnt snapshot emulator %i, ASIC %i'%(orbsyn_cnt_snapshot_emu,orbsyn_cnt_snapshot_asic))

    for i in range(12):
        # status should be 0x3
        # alignment patern should be in snapshot
        print('LINK %i:'%i)
        snapshot = read_asic['RO']['CH_ALIGNER_%iINPUT_ALL'%i]['snapshot']
        sel = read_asic['RO']['CH_ALIGNER_%iINPUT_ALL'%i]['select']
        status = read_asic['RO']['CH_ALIGNER_%iINPUT_ALL'%i]['status']
        orbsyn_cnt_snapshot = read_asic['RW']['ALIGNER_ALL']['orbsyn_cnt_snapshot']
        print('Status: ',hex(status), ' Snapshot: ',hex(snapshot),' Select value: ',hex(sel))
        print('Snapshot ',hex(snapshot >> sel))
        try:
            assert status==0x03
        except AssertionError:
            print('Failed to align ECON-T channel %i, status: %i'%(i,status))
            raise

    # terminate i2c servers
    for key,proc in procs.items():
        proc.terminate()


