import argparse
import os
import zmq_controller as zmqctrl
import re
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
    parser.add_argument('--yaml', type=str, default=None, help="YAML file of registers to read from")
    parser.add_argument('--write', default=False, action='store_true', help='write registers when using yaml file, rather than just read')
    parser.add_argument('--listRegisters', default=False, action='store_true', help="Print a list of all registers, or only registers matching pattern in --name argument if supplied")
    
    args = parser.parse_args()

    ### adds capability to simply print the list of accessible registers.
    ### if '--name' argument is also supplied, it pattern matches to the name, printing only applicable registers
    if args.listRegisters:
        import json
        with open("zmq_i2c/reg_maps/ECON_I2C_dict.json") as f:
            names_to_register = json.load(f)
        if args.name:
            p2 = re.compile('^(\w*)\*(\w*)$')
            regList = []
            if p2.match(args.name):
                name_start, name_end = p2.match(args.name).groups()
            else:
                name_start=args.name
                name_end=''
            for reg in names_to_register.keys():
                if reg.startswith(name_start) and reg.endswith(name_end):
                    regList.append(reg)
            for r in regList:
                print(r)
        else:
            for r in names_to_register.keys():
                print(r)
        exit()

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

    readOnly=True
    if args.value:
        readOnly=False
    
    # build the config
    if args.name:
        import json
        with open("zmq_i2c/reg_maps/ECON_I2C_dict.json") as f:
            names_to_register = json.load(f)
        names = args.name.split(',')
        p = re.compile('^(\w*)\[(\d*)-(\d*)\](\w*)$')
        p2 = re.compile('^(\w*)\*(\w*)$')
        regList = []
        for n in names:
            if n=='ALL':
                regList = list(names_to_register.keys())
                break
            if p.match(n):
                a,b,c,d = p.match(n).groups()
                for i in range(int(b),int(c)+1):
                    regList.append(f"{a}{i}{d}")
            elif p2.match(n):
                name_start, name_end = p2.match(n).groups()
                for reg in names_to_register.keys():
                    if reg.startswith(name_start) and reg.endswith(name_end):
                        regList.append(reg)
            else:
                regList.append(n)

        if args.value:
            values_split = args.value.split(',')
            values = []
            p1 = re.compile('^\[(\w*)\]\*(\w*)$')
            p2 = re.compile('^(\w*)\*\[(\w*)\]$')
            for v in values_split:
                if p1.match(v):
                    x,n = p1.match(v).groups()
                    x = int(x,16) if x.startswith('0x') else int(x)
                    values += [x]*int(n)
                elif p2.match(v):
                    n,x = p2.match(v).groups()
                    x = int(x,16) if x.startswith('0x') else int(x)
                    values += [x]*int(n)
                else:
                    x = int(v,16) if v.startswith('0x') else int(v)
                    values += [x]
            if len(values)==1 and len(regList)>1:
                values = values*len(regList)

            if len(values) != len(regList):
                print(f'ERROR: Mismatch between number of registers ({len(regList)}) and number of values ({len(values)}) supplied')
                exit()

        from nested_dict import nested_dict
        config = nested_dict()
        for i,name in enumerate(regList):
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
        new_config = config.to_dict()
    elif args.yaml:
        from yaml import safe_load
        with open(args.yaml) as _file:
            new_config=safe_load(_file)
        readOnly= not args.write
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
            if (args.rw is None) or (args.block is None) or (args.register is None):
                print('Insufficient register information provided')
                exit()
            new_config = {"ECON-T": {args.rw: {args.block: {"registers":{args.register: {"value": value} } } } } }

    i2c_sockets = {}
    if new_config=={}:
        print('No registers specified to read or write')
        exit()

    for key in server.keys():
        i2c_sockets[key] = zmqctrl.i2cController("localhost", str(server[key]))

        i2c_sockets[key].update_yamlConfig(yamlNode=new_config)


        # write only if value is given
        if not readOnly:
            i2c_sockets[key].configure()
        # read back i2c 
        read_socket = i2c_sockets[key].read_config(yamlNode=new_config)
        # print(read_socket)
        for access,accessDict in read_socket.items():
            for block,blockDict in accessDict.items():
                for param, paramDict in blockDict.items():
                    print(access,block, param, hex(read_socket[access][block][param]))

    # terminate i2c servers
    for key,proc in procs.items():
        proc.terminate()


