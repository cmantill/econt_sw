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
    parser.add_argument('--i2c',  type=str, default='ASIC', help="keys of i2c addresses(ASIC,emulator)")
    parser.add_argument('--name', type=str, default=None, help='Write name from dictionary')
    parser.add_argument('--rw', type=str, default=None, help='Read/Write permissions of register')
    parser.add_argument('--block', type=str, default=None, help="Register's block")
    parser.add_argument('--register', type=str, default=None, help="Register's name")
    parser.add_argument('--parameter', type=str, default=None, help="Parameter's name")
    parser.add_argument('--value', type=str, default=None, help="Value to write")
    
    args = parser.parse_args()

    i2ckeys = [args.i2c]
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

    # build the config
    if args.name:
        import json
        with open("zmq_i2c/reg_maps/ECON_I2C_dict.json") as f:
            names_to_register = json.load(f)

        if args.value:
            try:
                values = args.value.split(',')
            except:
                values = [args.value]

        from nested_dict import nested_dict
        config = nested_dict()
        for i,name in enumerate(args.name.split(',')):
            if name in names_to_register:
                rw = names_to_register[name][0]
                block = names_to_register[name][1]
                register = names_to_register[name][2]

                if args.value:
                    value = int(values[i])
                else:
                    value = 0

                if len(names_to_register[name])>3:
                    param =names_to_register[name][3]
                    config["ECON-T"][rw][block]["registers"][register]["params"][param] = {"param_value": value}
                else:
                    config["ECON-T"][rw][block]["registers"][register] = {"value": value}
            else:
                print(f'---register {name} not found')
        new_config = {}
        for i in config.keys():
            new_config[i] = {}
            for j in config[i].keys():
                new_config[i][j] = {}
                for k in config[i][j].keys():
                    new_config[i][j][k] = {}
                    for h in config[i][j][k].keys():
                        new_config[i][j][k][h] = {}
                        for g,val in config[i][j][k][h].items():
                            if 'params' in config[i][j][k][h][g].keys():
                                new_config[i][j][k][h][g] ={}
                                for d in  config[i][j][k][h][g].keys():
                                    new_config[i][j][k][h][g][d] = {}
                                    for s in config[i][j][k][h][g][d].keys():
                                        #print(config[i][j][k][h][g][d][s])
                                        new_config[i][j][k][h][g][d][s] = config[i][j][k][h][g][d][s]
                            else:
                                new_config[i][j][k][h][g] = config[i][j][k][h][g]
        #print(new_config)
    else:
        if args.parameter:
            parameters = args.parameter.split(',')
            if args.value:
                try:
                    values = args.value.split(',')
                except:
                    values = [args.value]
            else:
                values = [0 for p in parameters]
            new_config = {"ECON-T": {args.rw: {args.block: {"registers":{args.register: {"params": dict.fromkeys(parameters)} } } } } }
            for p,parameter in enumerate(parameters):
                new_config["ECON-T"][args.rw][args.block]["registers"][args.register]["params"][parameter] = {"param_value": int(values[p])}
        else:
            if args.value:
                value = args.value
            else: 
                value = 0
            new_config = {"ECON-T": {args.rw: {args.block: {"registers":{args.register: {"value": value} } } } } }
            
    i2c_sockets = {}
    for key in server.keys():
        i2c_sockets[key] = zmqctrl.i2cController("localhost", str(server[key]))
        i2c_sockets[key].update_yamlConfig(yamlNode=new_config)

        # write only if value is given
        if args.value:
            i2c_sockets[key].configure()

        # read back i2c 
        read_socket = i2c_sockets[key].read_config(yamlNode=new_config)
        #print(read_socket)
        for access,accessDict in read_socket.items():
            for block,blockDict in accessDict.items():
                for param, paramDict in blockDict.items():
                    print(access,block, param, hex(read_socket[access][block][param]))

    # terminate i2c servers
    for key,proc in procs.items():
        proc.terminate()


