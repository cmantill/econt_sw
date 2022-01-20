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
    parser.add_argument("--capture", dest="capture", type=str, help="capture data with one of the options", default=None)
    parser.add_argument('--compare',dest="compare",action='store_true', default=False, help='use stream compare')
    parser.add_argument('--stime',dest="stime",type=float, default=0.001, help='time between word counts')
    parser.add_argument('--nlinks',dest="nlinks",type=int, default=13, help='active links')
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
    cmd = 'python testing/uhal/eventDAQ.py --idir %s'%(args.idir)
    if args.capture:
        cmd += ' --capture %s'%args.capture
    if args.compare:
        cmd += ' --compare --stime %.3f --nlinks %i'%(args.stime,args.nlinks)
    os.system(cmd)

    # terminate i2c servers
    for key,proc in procs.items():
        proc.terminate()
