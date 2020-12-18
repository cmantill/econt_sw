from yaml import safe_load, load, dump
import math

class Translator():
    """ Translate between (human-readable) config and corresponding address/register values. """

    def __init__(self):
         self.paramMap = self.__load_param_map("reg_maps/ECON_I2C_params_regmap.yaml")
         self.pairs_from_cfg(self.paramMap['econ'])
         
    def __load_param_map(self, fname):
        """ Load a yaml register map into cache (as a dict). """
        with open(fname) as fin:
            paramMap = safe_load(fin)
        return paramMap

    def pairs_from_cfg(self, cfg):
        """
        Convert an input config dict to address: value pairs
        Case 1: One parameter value has one register
        Case 2: Several parameter values share same register
        """
        cfg_str = dump(cfg)
        pairs = {}
        for block in cfg:
            for access in cfg[block]:
                for param, paramDict in  cfg[block][access].items():
                    addr = paramDict['register'] + paramDict['reg_mask']
                    if addr in pairs: prev_regVal = pairs[addr]
                    # elif addr in writeCache: prev_regVal = writeCache[addr]
                    else:
                        prev_regVal = 0
                        # prev_regVal = list(roc.read([[{addr:0}]]).values())[0]
                    # convert parameter value (from config) into register value
                    paramVal = paramDict['default']
                    val = (paramVal & paramDict['param_mask']) << paramDict['param_shift']
                    pairs[addr] = prev_regVal + val
                    
        for p,pp in pairs.items():
            print(hex(p), hex(pp))

Translator()
