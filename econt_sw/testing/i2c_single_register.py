import argparse
import os
import zmq_controller as zmqctrl

"""
Writing a single i2c register.
- One needs to provide:
  - rw: permissions of register [rw,ro,wo]
  - block: block of register
  - register: name of register
  - parameter: OPTIONAL if writing only to a parameter
  - value: value of register or parameter
- One can use an existing server with an ADDRESS and PORT or start one with `--start-server`

e.g.

python3 testing/i2c_single_register.py --i2c ASIC --addr 0  --server 5554  --rw RW --block ALIGNER_ALL --register orbsyn_cnt_snapshot

and for writing a value:

python3 testing/i2c_single_register.py --i2c ASIC --addr 0  --server 5554  --rw RW --block ALIGNER_ALL --register orbsyn_cnt_snapshot --value 3
"""

import logging
logger = logging.getLogger("i2c")
logger.setLevel(logging.INFO)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Align links')
    parser.add_argument('--start-server', dest="start_server", action='store_true', default=False, help='start servers directly in script (for debugging is better to do it separately)')
    parser.add_argument('--addr', type=str, default='0', help='list of i2c list of addresses - e.g. 0 for ASIC, 1 for emulator')
    parser.add_argument('--server', type=str, default='5554', help='list of i2c server ports - e.g. 5554 for ASIC, 5555 for emulator')
    parser.add_argument('--i2c',  type=str, nargs="+", choices=['ASIC', 'emulator'], help="keys of i2c addresses")
    parser.add_argument('--rw', type=str, default='RW', help='Read/Write permissions of register')
    parser.add_argument('--block', type=str, required=True, help="Register's block")
    parser.add_argument('--register', type=str, required=True, help="Register's name")
    parser.add_argument('--parameter', type=str, default=None, help="Paramer's name")
    parser.add_argument('--value', type=int, default=None, help="Value to write")
    
    args = parser.parse_args()

    i2ckeys = args.i2c
    addresses = [int(addr) for addr in args.addr.split(',')]
    servers = [int(server) for server in args.server.split(',')]
    addr = {}; server={}; 
    for k,key in enumerate(i2ckeys):
        addr[key] = addresses[k]
        server[key] = str(servers[k])
    logger.info('Addresses %s',addr)
    logger.info('Servers %s',server)

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
        i2c_sockets[key] = zmqctrl.i2cController("localhost", str(server[key]))
        value = 0
        if args.value: value = args.value

        if args.parameter:
            new_config = {"ECON-T": {args.rw: {args.block: {"registers":{args.register: {"params": {args.parameter: {"param_value": value} } } } } } } }
        else:
            new_config = {"ECON-T": {args.rw: {args.block: {"registers":{args.register: {"value": value} } } } } }
        i2c_sockets[key].update_yamlConfig(yamlNode=new_config)

        # write only if value is given
        if args.value:
            i2c_sockets[key].configure()

        # read back i2c 
        read_socket = i2c_sockets[key].read_config(yamlNode=new_config)
        for access,accessDict in read_socket.items():
            for block,blockDict in accessDict.items():
                for param, paramDict in blockDict.items():
                    print(access,block, param, hex(read_socket[access][block][param]))

    # terminate i2c servers
    for key,proc in procs.items():
        proc.terminate()


