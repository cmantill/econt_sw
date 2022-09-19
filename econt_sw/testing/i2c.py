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
# ch = logging.StreamHandler()
# ch.setLevel(logging.INFO)
# formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
# ch.setFormatter(formatter)
# logger.addHandler(ch)

import time

class I2C_Client():
    def __init__(self,
                 ip='localhost',
                 servers={'ASIC':{'port':'5554','addr':0x20},
                          'emulator':{'port':'5555','addr':0x21}
                      },
                 forceLocal=False,
                 ):
        self.i2c_sockets = {}
        for key in servers:
            self.i2c_sockets[key] = i2cController(ip, 
                                                  port=servers[key]['port'],
                                                  addr=servers[key]['addr'],
                                                  forceLocal=forceLocal)

    def call(self,
             args_name=None,
             args_yaml=None,
             args_i2c='ASIC',
             args_value=None,
             args_write=False):

        if not (args_name or args_yaml):
            logger.error('Must specify either a register name or yaml file')
            exit()

        readOnly=True
        if args_value:
            readOnly=False

        chips=[]
        if 'ASIC' in args_i2c:
            chips.append('ASIC')
        if 'emulator' in args_i2c:
            chips.append('emulator')
        
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

        outputs={}
        for key in chips:
            if not readOnly:
                self.i2c_sockets[key].update_yamlConfig(yamlNode=new_config)
                self.i2c_sockets[key].configure()
            outputs[key]=self.i2c_sockets[key].read_config(yamlNode=new_config)

        return outputs

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Align links')
    parser.add_argument('--i2c',  type=str, default='ASIC', help="keys of i2c addresses(ASIC,emulator)")
    parser.add_argument('--name', type=str, default=None, help='Write name from dictionary')
    parser.add_argument('--value', type=str, default=None, help="Value to write")
    parser.add_argument('--yaml', type=str, default=None, help="YAML file of registers to read from")
    parser.add_argument('--write', default=False, action='store_true', help='write registers when using yaml file, rather than just read')
    parser.add_argument('--listRegisters', default=False, action='store_true', help="Print a list of all registers, or only registers matching pattern in --name argument if supplied")
    parser.add_argument('--info', default=False, action='store_true', help="Print a description of the register matching pattern in --name argument")
    parser.add_argument('--ip', type=str, default='localhost', help="IP address of server (default localhost)")
    parser.add_argument('--local', default=False, action='store_true', help="Skip using socket")
    parser.add_argument('--quiet', default=False, action='store_true', help="quiet mode, don't print output")
    
    args = parser.parse_args()

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
        try:
            with open("zmq_i2c/reg_maps/ECON_I2C_reg_description_dict.json") as f:
                registerDescriptions = json.load(f)
        except:
            registerDescriptions=None
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
                if not registerDescriptions is None:
                    print(f'    Description : {registerDescriptions[regInfo["docName"]]}')


        exit()

    i2cClient=I2C_Client(ip=args.ip,forceLocal=args.local)

    outputs =i2cClient.call(args_name=args.name,
                            args_value=args.value,
                            args_yaml=args.yaml,
                            args_write=args.write,
                        )

    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s')

    if not args.quiet:
        for key,read_socket in outputs.items():
            logger.info(key)
            for access,accessDict in read_socket.items():
                for block,blockDict in accessDict.items():
                    for param, paramDict in blockDict.items():
                        x = hex(read_socket[access][block][param])
                        logger.info(f'{access} {block} {param} {x}')
