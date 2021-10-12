import argparse
import os
import zmq_controller as zmqctrl

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Align links')
    parser.add_argument('--start-server', dest="start_server", action='store_true', default=False, help='start servers directly in script (for debugging is better to do it separately)')
    parser.add_argument('--prbs28', dest='prbs28',  action='store_true', default=False, help='PRBS 28 bit')
    parser.add_argument('--prbs32', dest='prbs32',  action='store_true', default=False, help='PRBS 32 bit')
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
    #print(read_asic)
    for i in range(12):
        # status should be 0x3
        # alignment patern should be in snapshot
        print('LINK %i:'%i)
        snapshot = read_asic['RO']['CH_ALIGNER_%iINPUT_ALL'%i]['snapshot']
        sel = read_asic['RO']['CH_ALIGNER_%iINPUT_ALL'%i]['select']
        status = read_asic['RO']['CH_ALIGNER_%iINPUT_ALL'%i]['status']
        print('Status: ',hex(status), ' Snapshot: ',hex(snapshot),' Select value: ',hex(sel))
        print('Snapshot ',hex(snapshot >> sel))
        try:
            assert status==0x03
        except AssertionError:
            print('Failed to align ECON-T channel %i, status: %i'%(i,status))
            raise

    # relative alignment for IO
    os.system('python testing/uhal-align_on_tester.py --step asic-tester')

    if args.prbs28 or args.prbs32:
        # prbs
        i2c_sockets = {}
        for key in ['ASIC']:
            print('writing prbs settings to %s'%key)
            i2c_sockets[key] = zmqctrl.i2cController("localhost", str(server[key]), "configs/align.yaml")
            
            i2c_sockets[key].yamlConfig['ECON-T']['RW']['FMTBUF_ALL']['registers']['tx_sync_word']['value'] = 0b00100100010        
            
            i2c_sockets[key].yamlConfig['ECON-T']['RW']['CH_ALIGNER_*INPUT_ALL']['registers']['config']['per_ch_align_en'] = {'param_value': 1}
            i2c_sockets[key].yamlConfig['ECON-T']['RW']['CH_ALIGNER_*INPUT_ALL']['registers']['config']['sel_override_en'] = {'param_value': 0}
            
            i2c_sockets[key].yamlConfig['ECON-T']['RW']['CH_ALIGNER_*INPUT_ALL']['registers']['config']['prbs_chk_en'] = {'param_value': 1}
            if args.prbs28:
                i2c_sockets[key].yamlConfig['ECON-T']['RW']['CH_ALIGNER_*INPUT_ALL']['registers']['config']['prbs28_en'] = {'param_value': 1}
            else:
                i2c_sockets[key].yamlConfig['ECON-T']['RW']['CH_ALIGNER_*INPUT_ALL']['registers']['config']['prbs28_en'] = {'param_value': 0}
            i2c_sockets[key].yamlConfig['ECON-T']['RW']['CH_ALIGNER_*INPUT_ALL']['registers']['sel_override_val'] = {'value': 0}
            i2c_sockets[key].configure()
            
            #if args.select!=-1:
            #    print('Setting select value to ',args.select)
            #    i2c_sockets[key].yamlConfig['ECON-T']['RW']['CH_ALIGNER_*INPUT_ALL']['registers']['config']['sel_override_en'] = {'param_value': 1}
            #    i2c_sockets[key].yamlConfig['ECON-T']['RW']['CH_ALIGNER_*INPUT_ALL']['registers']['sel_override_val'] = {'value': args.select}
            
            print('i2c settings for %s'%key)
            print('CH_ALIGNER_*INPUT_ALL: ', i2c_sockets[key].yamlConfig['ECON-T']['RW']['CH_ALIGNER_*INPUT_ALL'])
            print('ALIGNER_ALL: ', i2c_sockets[key].yamlConfig['ECON-T']['RW']['ALIGNER_ALL'])
            print('FMTBUF_ALL: ',i2c_sockets[key].yamlConfig['ECON-T']['RW']['FMTBUF_ALL'])
            i2c_sockets[key].configure()
            
            i2c_sockets[key].yamlConfig['ECON-T']['RW']['CH_ALIGNER_*INPUT_ALL']['registers']['config']['prbs_chk_en'] = {'param_value': 0}
            i2c_sockets[key].configure()
            
            i2c_sockets[key].yamlConfig['ECON-T']['RW']['CH_ALIGNER_*INPUT_ALL']['registers']['config']['prbs_chk_en'] = {'param_value': 1}
            i2c_sockets[key].configure()
        
        if args.prbs28:
            print('Sending prbs 28 bit w elinkoutputs')
            os.system('python testing/uhal-prbs.py --prbs28')
        else:
            print('Sending prbs 32 bit w elinkoutputs')
            os.system('python testing/uhal-prbs.py')

        # read 
        for key in ['ASIC']:
            print('reading %s'%key)
            read = i2c_sockets[key].read_config("configs/prbs.yaml","read")
            for i in range(12):
                print('Status prbs chck err %i'%i,hex(read['RO']['CH_ALIGNER_%iINPUT_ALL'%i]['status_prbs_chk_err']))
                print('Status hdr err %i '%i,hex(read['RO']['CH_ALIGNER_%iINPUT_ALL'%i]['status_hdr_mm_err']))
                print('Snapshot link %i'%i,hex(read['RO']['CH_ALIGNER_%iINPUT_ALL'%i]['snapshot']))
                print('Select value link %i'%i,hex(read_asic['RO']['CH_ALIGNER_%iINPUT_ALL'%i]['select']))

    # terminate i2c servers
    for key,proc in procs.items():
        proc.terminate()
