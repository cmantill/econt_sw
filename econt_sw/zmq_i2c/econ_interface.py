from translator import Translator
from econ_i2c import econ_i2c
import yaml

class econ_interface():
    """ Base class for interfacing with ECON at i2c register level """

    def __init__(self, addr=0x20):
        self.i2c = econ_i2c(1)
        self.translator = Translator('ECON-T')
        self.i2c_addr = addr
        self.writeCache = {}

    def configure(self, cfg=None):
        """ Configure ECON i2c and return when finished """
        # read all default register:address pairs into a default dict
        default = self.translator.pairs_from_cfg()

        if cfg:
            # load and expand config
            paramMap = self.translator.load_param_map(cfg)['ECON-T']
            pairs = self.translator.pairs_from_cfg(paramMap)

            # read previous values of addresses 
            self.writeCache = self.read_pairs(pairs)

            # get new default values
            writePairs = self.translator.pairs_from_cfg(paramMap,prevCache=self.writeCache)
        else:
            # read previous values of addresses
            self.writeCache = self.read_pairs(default)
            
            # get new default values 
            writePairs = self.translator.pairs_from_cfg(prevCache=self.writeCache)
        
        # write registers
        self.write_pairs(writePairs)
        return "i2c: ECON Configured"

    def read(self, cfg=None):
        """ Read from configs or cache """
        # print('read from configs or cache ',cfg)
        if cfg: 
            return self.__read_fr_cfg(cfg)
        else: 
            return self.__read_fr_cache()

    def read_pairs(self, pairs):
        """ Read addresses in addr:val pairs """
        # print('read_pairs ',pairs)
        pairs_read = {}
        for addr,vals in pairs.items():
            size_byte = vals[1]
            pairs_read[addr] = self.__read_I2C_reg(addr, size_byte)
        return pairs_read

    def write_pairs(self, pairs):
        """ Write addresses in addr:val pairs. """
        # TODO: implement burst reading/writing
        for addr,vals in pairs.items():
            val = vals[0]
            size_byte = vals[1]
            self.__set_I2C_reg(addr, val)

    def __read_fr_cfg(self, cfg):
        """ Read addresses (=keys) in cfgs from rocs. """
        # print('read fr cfg')
        # TODO: make this for multiple cfgs?
        paramMap = self.translator.load_param_map(cfg)['ECON-T']
        pairs = self.translator.pairs_from_cfg(paramMap, self.writeCache)
        rd_pairs = self.read_pairs(pairs)
        cfgRead = self.translator.cfg_from_pairs(rd_pairs,cfg)
        return cfgRead

    def __read_fr_cache(self):
        """ Read addresses in write_param cache. """
        # print('read fr cache ')
        rd_pairs = self.read_pairs(self.writeCache)
        return rd_pairs

    def __read_I2C_reg(self, addr, size_byte):
        """ Read byte from register. """
        try: 
            return self.i2c.read(self.i2c_addr, addr, size_byte)
        except IOError as e:
            print('IOError in read. Attempting re-read.')
            self.__read_I2C_reg(addr, size_byte)
        except Exception: raise     # For all other errors reset the I2C state machine and the chip.

    def __set_I2C_reg(self, addr, val):
        """
        Write byte to register.
        """
        try:
            return self.i2c.write(self.i2c_addr, addr, val)
        except IOError as e:
            print('IOError in write. Attempting re-write.')
            self.__set_I2C_reg(addr, val)
        except Exception: raise  # For all other errors reset the I2C state machine and the chip.
