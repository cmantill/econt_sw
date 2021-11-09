import argparse
import os
import zmq_controller as zmqctrl

"""
event DAQ

python3 testing/eventDAQ.py --idir  configs/test_vectors/counterPatternInTC/ --start-server
"""

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Event DAQ')
    parser.add_argument('--start-server', dest="start_server", action='store_true', default=False, help='start servers directly in script (for debugging is better to do it separately)')
    parser.add_argument('--idir',dest="idir", type=str, required=True, default=None, help='test vector directory')
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

    procs = {}
    if args.start_server:
        for key in server.keys():
            procs[key] = Popen(cmds[key], cwd=cwds[key],stdout=PIPE, universal_newlines=True, env=env)

    i2c_sockets = {}
    for key in server.keys():
        inityaml = args.idir+"/init.yaml"
        try:
            i2c_sockets[key] = zmqctrl.i2cController("localhost", str(server[key]), args.idir+"/init.yaml")
        except:
            inityaml = args.idir+"/init_%s.yaml"%key
            i2c_sockets[key] = zmqctrl.i2cController("localhost", str(server[key]), args.idir+"/init_%s.yaml"%key)
        i2c_sockets[key].configure()

        # read back i2c 
        read_socket = i2c_sockets[key].read_config(inityaml)
        #print(read_socket)


    # daq
    os.system('python testing/uhal-eventDAQ.py --idir %s --capture l1a'%args.idir)

    # terminate i2c servers
    for key,proc in procs.items():
        proc.terminate()
