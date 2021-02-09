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
        self.regDict = {}
        self.nInputChannels = self.paramMap['ninput']
        self.nOutputChannels = self.paramMap['noutput']

    def load_param_map(self, fname):
        """ Load a yaml register map into cache (as a dict). """
        with open(fname) as fin:
            paramMap = safe_load(fin)
        return paramMap

    def cfg_from_pairs(self, pairs):
        """
        Convert from {addr:val} pairs to {param:param_val} config.
        We can only recover a parameter from a pair when it is in the common cache.
        """
        cfg = nested_dict()
        for access, accessDict in self.__regs_from_paramMap.cache.items():
            for block, blockDict in accessDict.items():
                for param, paramDict in blockDict.items():
                    addr = paramDict['addr']
                    prev_regVal = cfg[access][block][param] if cfg[access][block][param]!={} else 0
                    paramVal = int.from_bytes(pairs[addr], 'little')
                    cfg[access][block][param] = paramVal
                    
        return cfg.to_dict()

    def pairs_from_cfg(self, cfg, writeCache):
        """
        Convert an input config dict to address: value pairs
        Case 1: One parameter value has one register
        Case 2: Several parameter values share same register
        Case 3: A block of registers is `repeated` for the number of input channels (*)
        Case 4: A block of parameters for a given register is `repeated` for the number of input channels (*)
        """
        cfg_str = dump(cfg)
        pairs = {}
        for access in cfg:
            if access=='ninput' or access=='noutput': continue
            # should replace this w. config
            par_regs = self.__regs_from_paramMap(access)
            for block,blockDict in par_regs.items():
                for param, paramDict in blockDict.items():
                    addr = paramDict['addr']
                    size_byte = paramDict['size_byte']

                    # check if values are given in the config - otherwise they are taken from the default map
                    paramVal = paramDict['val']
                    if block in cfg[access] and addr in writeCache:
                        prev_regVal = writeCache[addr][0]
                        if param in cfg[access][block]['registers']:
                            reg = cfg[access][block]['registers'][param]
                            if 'value' in reg: paramVal = reg['value']
                            if 'params' in reg: 
                                tmpparamDict = paramDict['params']
                                for par, parreg in reg['params'].items():
                                    tmpparamDict[par]['param_value'] = parreg['param_value']
                                paramVal = self.__regVal_from_paramValues(tmpparamDict)
                    #elif addr in pairs:
                    #    prev_regVal = int.from_bytes(pairs[addr], 'little')
                    #else:
                    #    prev_regVal = 0
                        
                    #print(param,block,paramVal,prev_regVal)
                    # convert parameter value (from config) into register value
                    #val = prev_regVal + paramVal
                    val = paramVal
                    if size_byte > 1:
                        pairs[addr] = list(val.to_bytes(size_byte, 'little'))
                    else:
                        pairs[addr] = [val]

        return pairs

    @memoize
    def __regs_from_paramMap(self, access):
        """ Expand json parameter Map into full dictionary of:
            'register': {'addr': X,
                         'size_byte': X,
                         'value': X}
        """
        self.regDict[access] = {}
        for block,blockDict in self.paramMap[access].items():
            block_shift = blockDict['block_shift'] if 'block_shift' in blockDict else 0
            addr_base = blockDict['addr_base']
            if '*' in block:
                nchannels = self.nInputChannels if '*INPUT' in block else self.nOutputChannels
                block_names = [block.replace('*','%i'%i) for i in range(nchannels)]
                for i in range(nchannels):
                    self.regDict[access][block_names[i]] = {}
            else:
                self.regDict[access][block] = {}
                
            for param, paramDict in blockDict['registers'].items():
                addr_offset = paramDict['addr_offset'] if 'addr_offset' in paramDict else 0
                address = addr_base + addr_offset
                size_byte = paramDict['size_byte'] if 'size_byte' in paramDict else 1
                values = paramDict['value'] if 'value' in paramDict else None

                # if this register has parameters for the same address
                parDict = paramDict['params'] if 'params' in paramDict else {}

                # if not default value given derive it from the default value of the parameters of that register
                if values is None:
                    try:
                        defaults = [reg['param_value'] for reg in param_dict.values()]
                    except:
                        print('no default value given of the register or of the parameters of the register')
                        raise
                    values = self.__regVal_from_paramValues(parDict)
                
                if '*' in param:
                    try:
                        for i in range(len(values)):
                            reg_name = param.replace('*','%i'%i)
                            reg_addr = address + i*paramDict['addr_shift']
                            self.regDict[access][block][reg_name] = {'addr': reg_addr,
                                                                     'val': values[i],
                                                                     'size_byte': size_byte,
                                                                     'params': parDict,
                                                                     }
                    except:
                        print('list of parameters but no shift of address')
                        raise
                elif '*' in block:
                    try:
                        nchannels = self.nInputChannels if '*INPUT' in block else self.nOutputChannels
                        for i in range(nchannels):
                            block_name = block.replace('*','%i'%i)
                            reg_name = param
                            reg_addr = address + i*block_shift
                            self.regDict[access][block_name][reg_name] = {'addr': reg_addr,
                                                                          'val': values,
                                                                          'size_byte': size_byte,
                                                                          'params': parDict,
                                                                          }
                    except:
                        print('no block shift in block dictionary')
                        raise
                else:
                    self.regDict[access][block][param] = {'addr': address,
                                                          'val': values,
                                                          'size_byte': size_byte,
                                                          'params': parDict,
                                                          }
                    
        return self.regDict[access]
    
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
