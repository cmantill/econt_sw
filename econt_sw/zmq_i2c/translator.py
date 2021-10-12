import functools
from yaml import safe_load, load, dump
from nested_dict import nested_dict
import math

def memoize(fn):
    """ Readable memoize decorator. """
    fn.cache = {}
    @functools.wraps(fn)
    def inner(inst, *key):
        if key not in fn.cache:
            fn.cache[key] = fn(inst, *key)
        return fn.cache[key]
    return inner

class Translator():
    """ Translate between (human-readable) config and corresponding address/register values. """

    def __init__(self,econ):
        self.econ = econ
        self.paramMap = self.load_param_map("reg_maps/ECON_I2C_params_regmap.yaml")[self.econ]
        self.regDict = nested_dict()
        self.nInputChannels = self.paramMap['ninput']
        self.nOutputChannels = self.paramMap['noutput']

    def load_param_map(self, fname):
        """ Load a yaml register map into cache (as a dict). """
        if isinstance(fname, dict):
            paramMap = fname
        else:
            with open(fname) as fin:
                paramMap = safe_load(fin)
        return paramMap

    def cfg_from_pairs(self, pairs, config=None):
        """
        Convert from {addr:[val,size_byte]} pairs to {param:param_val} config.
        We can only recover a parameter from a pair when it is in the common cache.
        However, when we read (or write) a param the common cache is populated in advance.
        """
        if config:
            read_cfg = self.__expandVal_paramMap(config['ECON-T'])
        cfg = nested_dict()
        for access,accessDict in self.__regs_from_paramMap.cache[()].items():
            for block,blockDict in accessDict.items():
                for param, paramDict in blockDict.items():
                    addr = paramDict['addr']
                    if addr in pairs.keys():
                        if isinstance(pairs[addr][0],list):
                            reg_value = int.from_bytes(pairs[addr][0], 'little')
                        else:
                            reg_value = pairs[addr][0]
                        cfg[access][block][param] = reg_value

                        if config:
                            for read_par in read_cfg[access][block][param]['params']:
                                if read_par in paramDict['params'].keys():
                                    tmpVal = self.__paramVal_from_regVal(paramDict['params'][read_par], reg_value) 
                                    cfg[access][block][param + '_' + read_par] = tmpVal

        return cfg.to_dict()

    def pairs_from_cfg(self, cfg=None, prevCache={}, allowed=['RW','RO']):
        """
        Convert an input config dict to pairs of
        {address: [value, size_byte]}
        """
        pairs = {}
        par_regs = self.__regs_from_paramMap() # default map
        par_regs_cfg = self.__expandVal_paramMap(cfg) if cfg else par_regs # new config, if any

        # print('Translator::Converting config into pairs')
        for access,accessDict in par_regs_cfg.items():
            if access not in allowed: continue
            for block,blockDict in accessDict.items():
                for param, paramDict in blockDict.items():
                    # read keys from the default dict
                    defaultDict = par_regs[access][block][param]
                    addr = defaultDict['addr']
                    size_byte = defaultDict['size_byte']

                    # values are taken from the default map if not in the cfg
                    paramVal = defaultDict['val']

                    is_infg = False
                    try:
                        # print(access,block,param)
                        cfgDict = par_regs_cfg[access][block][param]
                        is_incfg = True
                    except KeyError:
                        print('no cfgDict')
                        pass

                    if is_incfg and cfgDict is not None:
                        if 'val' in cfgDict:
                            paramVal = cfgDict['val']
                        elif 'params' in cfgDict:
                            tmpparamDict = defaultDict['params']
                            # previous register value should be read from i2c
                            prev_regVal = int.from_bytes(prevCache[addr][0], 'little') if addr in prevCache else 0
                            for par, reg in defaultDict['params'].items():
                                # get parameter values from previous register value 
                                # TODO: does this do something?
                                tmpVal = self.__paramVal_from_regVal(reg, prev_regVal)
                                # get parameter values from new dict
                                if par in cfgDict['params']:
                                    tmpVal =  cfgDict['params'][par]['param_value']
                                tmpparamDict[par]['param_value'] = tmpVal
                            paramVal = self.__regVal_from_paramValues(tmpparamDict)
                        else:
                            print('WARNING: No value given for register ',param)
                            paramVal = 0
                                
                    # convert parameter value (from config) into register value
                    # print('addr ',hex(addr), ' val ',paramVal, ' size_byte  ', size_byte)
                    pairs[addr] = [paramVal.to_bytes(size_byte, 'little'),size_byte]

        return pairs

    def convert_pairs(self, pairs,direction='to'):
        new_pairs = {}
        for addr in pairs.keys():
            size_byte = pairs[addr][1]
            if direction=='from':
                reg_value = list(pairs[addr][0])
            else:
                reg_value = pairs[addr][0].from_bytes(size_byte, 'little')
            new_pairs[addr] = [reg_value, pairs[addr][1]]
        return new_pairs
    
    @memoize
    def __regs_from_paramMap(self):
        for access,accessDict in self.paramMap.items():
            if not isinstance(accessDict, dict): continue
            for block,blockDict in accessDict.items():
                block_shift = blockDict['block_shift'] if 'block_shift' in blockDict else 0
                addr_base = blockDict['addr_base']
                for param, paramDict in blockDict['registers'].items():
                    addr_offset = paramDict['addr_offset'] if 'addr_offset' in paramDict else 0
                    address = addr_base + addr_offset
                    size_byte = paramDict['size_byte'] if 'size_byte' in paramDict else 1
                    parDict = paramDict['params'] if 'params' in paramDict else {}

                    if '*' in param:
                        try:
                            for i in range(paramDict['n_iterations']):
                                reg_name = param.replace('*','%i'%i)
                                reg_addr = address + i*paramDict['addr_shift']
                                self.regDict[access][block][reg_name] = {'addr': reg_addr,
                                                                         'size_byte': size_byte,
                                                                         'params': parDict,
                                                                         }
                        except:
                            pass

                    elif '*' in block:
                        try:
                            nchannels = self.nInputChannels if '*INPUT' in block else self.nOutputChannels
                            for i in range(nchannels):
                                block_name = block.replace('*','%i'%i)
                                reg_name = param
                                reg_addr = address + i*block_shift
                                self.regDict[access][block_name][reg_name] = {'addr': reg_addr,
                                                                              'size_byte': size_byte,
                                                                              'params': parDict,
                                                                              }
                        except:
                            print('no block shift in block dictionary') 
                            pass

                    else:
                        self.regDict[access][block][param] = {'addr': address,
                                                              'size_byte': size_byte,
                                                              'params': parDict,
                                                              }
        # fill dictionary with default values
        nDict = self.__expandVal_paramMap(self.paramMap)
        self.regDict.update(nDict)
        return self.regDict

    def __expandVal_paramMap(self, cfg):
        """ 
        Expand parameter values json into dictionary        
        Case 1: One parameter value has one register
        Case 2: Several parameter values share same register
        Case 3: A block of registers is `repeated` for the number of channels (*)
        Case 4: A block of parameters for a given register is `repeated` for the number of channels (*) 
        """
        regDict = nested_dict()
        for access,accessDict in cfg.items():
            if not isinstance(accessDict, dict): continue
            for block,blockDict in accessDict.items():
                 for param, paramDict in blockDict['registers'].items():
                    values = paramDict['value'] if 'value' in paramDict else None
                    parDict = nested_dict()
                    if 'params' in paramDict:
                        # print(paramDict['params'],param,block)
                        for par,pDict in paramDict['params'].items():
                            if 'param_value' in pDict: parDict[par]['param_value'] = pDict['param_value']

                    if '*' in param:
                        if len(values)== self.paramMap[access][block]['registers'][param]['n_iterations']:
                            for i in range(len(values)):
                                reg_name = param.replace('*','%i'%i)
                                if values[i] is not None: regDict[access][block][reg_name]['val'] = values[i]
                                if bool(parDict): regDict[access][block][reg_name]['params'] = parDict
                    elif '*' in block:
                        nchannels = self.nInputChannels if '*INPUT' in block else self.nOutputChannels
                        for i in range(nchannels):
                            block_name = block.replace('*','%i'%i)
                            reg_name = param
                            if values is not None: regDict[access][block_name][reg_name]['val'] = values
                            if bool(parDict): regDict[access][block_name][reg_name]['params'] = parDict
                    else:
                        if values is not None: regDict[access][block][param]['val'] = values
                        if bool(parDict): regDict[access][block][param]['params'] = parDict
                            
        return regDict
    
    def __regVal_from_paramValues(self, param_dict, prev_param_value=0):
        """ Convert parameter values (from config dictionary) into register value. """
        reg_value = prev_param_value
        for par, reg in param_dict.items():
            param_val = (reg["param_value"] & reg["param_mask"])
            param_val <<= reg["param_shift"]
            reg_value |= param_val
        return reg_value

    def __paramVal_from_regVal(self, reg, reg_value):
        """ Convert register value into (part of) parameter value. """
        param_val = (reg_value >> reg["param_shift"])
        param_val &= reg["param_mask"]
        return param_val
