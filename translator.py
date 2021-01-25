from yaml import safe_load, load, dump
import math

class Translator():
    """ Translate between (human-readable) config and corresponding address/register values. """

    def __init__(self):
        self.paramMap = self.__load_param_map("reg_maps/ECON_I2C_params_regmap.yaml")
        #self.pairs_from_cfg(self.paramMap['econ'],{})

    def __load_param_map(self, fname):
        """ Load a yaml register map into cache (as a dict). """
        with open(fname) as fin:
            paramMap = safe_load(fin)
        return paramMap

    def pairs_from_cfg(self, cfg, writeCache):
        """
        Convert an input config dict to address: value pairs
        Case 1: One parameter value has one register
        Case 2: Several parameter values share same register
        TODO : Add cache/ read old values?
        """
        cfg_str = dump(cfg)
        pairs = {}
        for block in cfg:
            for access in cfg[block]:
                for param, paramDict in  cfg[block][access].items():
                    address = paramDict['register'] + paramDict['reg_offset']
                    values = paramDict['default']
                    if 'reg_shift' in paramDict:
                        addrList = [address + i*paramDict['reg_shift'] for i in range(len(values))]
                        try:
                            valList = values
                        except:
                            print('list of addresses but not values')
                    else:
                        addrList = [address]
                        valList = [values]
                    for i,addr in enumerate(addrList):
                        # previous register value
                        if addr in pairs:
                            if paramDict['size_byte'] > 1: prev_regVal = int.from_bytes(pairs[addr], 'little')
                            else: prev_regVal = pairs[addr][0]
                        elif addr in writeCache:
                            prev_paramVal = writeCache[addr][0]
                        else:
                            prev_regVal = 0
                            
                        # convert parameter value (from config) into register value
                        paramVal = valList[i]
                        if 'param_mask' in paramDict: paramVal = paramVal & paramDict['param_mask']
                        if 'param_shift' in paramDict: paramVal <<= paramDict['param_shift']
                        val = prev_regVal + paramVal
                        if paramDict['size_byte'] > 1:
                            pairs[addr] = list(val.to_bytes(paramDict['size_byte'], 'little'))
                        else:
                            pairs[addr] = [val]

        # testing
        '''
        for p,lpp in pairs.items():
            print(p,lpp)
            for pp in lpp:
                print(hex(p), hex(pp))
        '''
        return pairs
    
