import argparse
import os
from zmq_controller import i2cController
import re
"""
Writing to i2c
- One needs to provide:
  - rw: permissions of register [rw,ro,wo]
  - block: block of register
  - register: name of register
  - parameter: OPTIONAL if writing only to a parameter
  - value: value of register or parameter
- One can use an existing server with an ADDRESS and PORT or start one with `--start-server`
- If yaml option is provided it will read the values of those registers.
  - to write those values add `--write`
- One can also print the list of accessible registers with `list`
  - if '--name' argument is also supplied, it pattern matches to the name, printing only applicable registers 

e.g.

python3 testing/i2c.py --i2c ASIC --addr 0  --server 5554  --rw RW --block ALIGNER_ALL --register orbsyn_cnt_snapshot

and for writing a value:

python3 testing/i2c.py --i2c ASIC --addr 0  --server 5554  --rw RW --block ALIGNER_ALL --register orbsyn_cnt_snapshot --value 3
"""

import logging
logger = logging.getLogger("i2c")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

def compare_asic_emulator():
    server={"ASIC": 5554, "emulator": 5555}
    outputs = {}
    for key in server.keys():
        socket = i2cController('localhost', str(server[key]))
        outputs[key] = socket.read_config()
    print(outputs)
    
def call_i2c(args_name=None,
             args_rw=None,
             args_block=None,
             args_register=None,
             args_parameter=None,
             args_value=None,
             args_yaml=None,
             args_write=False,
             args_compare=False,
             args_i2c='ASIC',
             args_start_server=False,
             args_addr='0',
             args_ip='localhost',
             args_server='5554',
             args_init=False,
):
    # set default server (change if needed)
    if args_i2c=="emulator":
        args_addr = "1"
        args_server = "5555"
    if args_i2c=="ASIC,emulator" and args_server=="5554":
        args_addr = "0,1"
        args_server = "5554,5555"

    i2ckeys = [key for key in args_i2c.split(',')]
#    i2ckeys = [args_i2c]
    addresses = [int(addr) for addr in args_addr.split(',')]
    servers = [int(server) for server in args_server.split(',')]

    addr = {}; server={}; 
    for k,key in enumerate(i2ckeys):
        addr[key] = addresses[k]
        server[key] = str(servers[k])
    # logger.info('Addresses %s',addr)
    # logger.info('Servers %s',server)

    env = os.environ.copy()
    from subprocess import PIPE, Popen
    cmds = {}; cwds = {};
    for key in server.keys():
        cmds[key] = ['python3', '-u', 'zmq_server.py', '--addr', '%i'%(0x20+addr[key]), '--server', server[key]]
        cwds[key] = './zmq_i2c'

    procs = {}
    if args_start_server:
        for key in server.keys():
            procs[key] = Popen(cmds[key], cwd=cwds[key],stdout=PIPE, universal_newlines=True, env=env)

    readOnly=True
    if args_value:
        readOnly=False
    
    # build the config
    new_config=None
    if args_name:
        import json
        with open("zmq_i2c/reg_maps/ECON_I2C_dict.json") as f:
            names_to_register = json.load(f)
        names = args_name.split(',')
        p = re.compile('^(\w*)\[(\d*)-(\d*)\](\w*)$') #match to find a range of channels
        p2 = re.compile('^(\w*)\*(\w*)$') #match with asterisk for autocomplete
        p3 = re.compile('^(\w*)\*(\w*)\*(\w*)$') #match with two asterisks for autocompleting
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
            elif p3.match(n):
                name_start, name_mid, name_end = p3.match(n).groups()
                for reg in names_to_register.keys():
                    if reg.startswith(name_start) and reg.endswith(name_end) and (name_mid in reg):
                        regList.append(reg)
            elif n in ['RO','RW','WO']:
                for r,info in names_to_register.items():
                    if info[0]==n:
                        regList.append(r)
            else:
                regList.append(n)

        if args_value:
            values_split = args_value.split(',')
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
                logger.error(f'ERROR: Mismatch between number of registers ({len(regList)}) and number of values ({len(values)}) supplied')
                exit()

        from nested_dict import nested_dict
        config = nested_dict()
        for i,name in enumerate(regList):
            if name in names_to_register:
                rw = names_to_register[name][0]
                block = names_to_register[name][1]
                register = names_to_register[name][2]

                if args_value:
                    value = int(values[i])
                else:
                    value = 0

                if len(names_to_register[name])>3:
                    param =names_to_register[name][3]
                    config["ECON-T"][rw][block]["registers"][register]["params"][param] = {"param_value": value}
                else:
                    config["ECON-T"][rw][block]["registers"][register] = {"value": value}
            else:
                logger.error(f'---register {name} not found')
        new_config = config.to_dict()
    elif args_yaml:
        from yaml import safe_load
        with open(args_yaml) as _file:
            new_config=safe_load(_file)
        readOnly= not args_write
    elif args_init:
        pass
    else:
        if args_parameter:
            parameters = args_parameter.split(',')
            if args_value:
                try:
                    values = args_value.split(',')
                except:
                    values = [args_value]
            else:
                values = [0 for p in parameters]
            new_config = {"ECON-T": {args_rw: {args_block: {"registers":{args_register: {"params": dict.fromkeys(parameters)} } } } } }
            for p,parameter in enumerate(parameters):
                new_config["ECON-T"][args_rw][args_block]["registers"][args_register]["params"][parameter] = {"param_value": int(values[p])}
        else:
            if args_value:
                value = args_value
            else: 
                value = 0
            if ((args_rw is None) or (args_block is None) or (args_register is None)) and not args_compare:
                logger.error('Insufficient register information provided')
                exit()
            new_config = {"ECON-T": {args_rw: {args_block: {"registers":{args_register: {"value": value} } } } } }

    i2c_sockets = {}
    if new_config is None and not args_init:
        logger.error('No registers specified to read or write')
        exit()

    outputs = {}
    for key in server.keys():
        i2c_sockets[key] = i2cController(args_ip, str(server[key]))

        if args_init:
            i2c_sockets[key].initialize()
        else:
            i2c_sockets[key].update_yamlConfig(yamlNode=new_config)

        # write only if value is given
        if args_compare:
            i2c_read = i2c_sockets[key].read_and_compare()
            outputs[key] = i2c_read
            # i2c_read = i2c_sockets[key].read_and_compare('RO')
            # print(f'Unmatched RO {i2c_read}')
        elif not readOnly:
            i2c_sockets[key].configure()
            
        if not args_compare:
            # read back i2c 
            read_socket = i2c_sockets[key].read_config(yamlNode=new_config)

            outputs[key] = read_socket

    # terminate i2c servers
    for key,proc in procs.items():
        proc.terminate()
    return outputs

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
    parser.add_argument('--compare', default=False, action='store_true', help='do comparison of read to values in yaml file')
    parser.add_argument('--compare_asicemu', default=False, action='store_true', help='do comparison of read to values in yaml file')
    parser.add_argument('--listRegisters', default=False, action='store_true', help="Print a list of all registers, or only registers matching pattern in --name argument if supplied")
    parser.add_argument('--info', default=False, action='store_true', help="Print a description of the register matching pattern in --name argument")
    parser.add_argument('--ip', type=str, default='localhost', help="IP address of server (default localhost)")
    parser.add_argument('--init', default=False, action='store_true', help='write default register map')
    parser.add_argument('--quiet', default=False, action='store_true', help="quiet mode, don't print output")
    
    args = parser.parse_args()

    if args.compare_asicemu:
        compare_asic_emulator()
        exit()
        
    ### adds capability to simply print the list of accessible registers.
    ### if '--name' argument is also supplied, it pattern matches to the name, printing only applicable registers
    if args.listRegisters:
        import json
        with open("zmq_i2c/reg_maps/ECON_I2C_dict.json") as f:
            names_to_register = json.load(f)
        if args.name:
            p2 = re.compile('^(\w*)\*(\w*)$')
            p3 = re.compile('^(\w*)\*(\w*)\*(\w*)$') #match with two asterisks for autocompleting
            regList = []
            if p2.match(args.name):
                name_start, name_end = p2.match(args.name).groups()
                name_mid=''
            elif p3.match(args.name):
                name_start, name_mid, name_end = p3.match(args.name).groups()
            elif args.name in ['RO','RW','WO']:
                for r,info in names_to_register.items():
                    if info[0]==args.name:
                        print(info[0], r)
                exit()
            else:
                name_start=args.name
                name_mid=''
                name_end=''
            for reg in names_to_register.keys():
                if reg.startswith(name_start) and reg.endswith(name_end) and (name_mid in reg):
                    regList.append(reg)
            for r in regList:
                print(names_to_register[r][0], r)
        else:
            for r in names_to_register.keys():
                print(names_to_register[r][0], r)
#                print(r)
        exit()

    ### adds capability to simply print the list of accessible registers.
    ### if '--name' argument is also supplied, it pattern matches to the name, printing only applicable registers
    if args.info:
        import json
        with open("zmq_i2c/reg_maps/ECON_I2C_dict_info.json") as f:
            names_to_register = json.load(f)
        with open("zmq_i2c/reg_maps/ECON_I2C_reg_description_dict.json") as f:
            registerDescriptions = json.load(f)
        if args.name:
            p2 = re.compile('^(\w*)\*(\w*)$')
            p3 = re.compile('^(\w*)\*(\w*)\*(\w*)$') #match with two asterisks for autocompleting
            regList = []
            if p2.match(args.name):
                name_start, name_end = p2.match(args.name).groups()
                name_mid=''
            elif p3.match(args.name):
                name_start, name_mid, name_end = p3.match(args.name).groups()
            else:
                name_start=args.name
                name_mid=''
                name_end=''
            for reg in names_to_register.keys():
                if reg.startswith(name_start) and reg.endswith(name_end) and (name_mid in reg):
                    regList.append(reg)
            for r in regList:
                print(r)
                regInfo=names_to_register[r]
                print(f'    ReadWrite   : {regInfo["i2cInfo"][0]}')
                print(f'    Address     : {regInfo["addr"]}')
                print(f'    Size (bits) : {regInfo["size"]}')
                print(f'    Default     : {regInfo["default"]}')
                print(f'    Bits        : {regInfo["bits"]}')
                print(f'    Description : {registerDescriptions[regInfo["docName"]]}')


        exit()

    outputs = call_i2c(args_name=args.name,
                       args_rw=args.rw,
                       args_block=args.block,
                       args_register=args.register,
                       args_parameter=args.parameter,
                       args_value=args.value,
                       args_yaml=args.yaml,
                       args_write=args.write,
                       args_compare=args.compare,
                       args_i2c=args.i2c,
                       args_start_server=args.start_server,
                       args_addr=args.addr,
                       args_ip=args.ip,
                       args_server=args.server,
                       args_init=args.init,
    )


    if not args.quiet:
        for key,read_socket in outputs.items():
            logger.info(key)
            for access,accessDict in read_socket.items():
                for block,blockDict in accessDict.items():
                    for param, paramDict in blockDict.items():
                        x = hex(read_socket[access][block][param])
                        logger.info(f'{access} {block} {param} {x}')
