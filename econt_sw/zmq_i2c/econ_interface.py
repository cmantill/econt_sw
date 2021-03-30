from translator import Translator
from econ_i2c import econ_i2c
import yaml

class econ_interface():
    """ Base class for interfacing with ECON at i2c register level """

    def __init__(self):
        self.i2c = econ_i2c(1)
        self.translator = Translator('ECON-T')
        self.i2c_addr = 0x20
        self.writeCache = {}

    def configure(self, cfg=None):
        """ Configure ECON i2c and return when finished """
        # read all default register:address pairs into a default dict
        default = self.translator.pairs_from_cfg()

        print('read all default ')
        if cfg:
            print('load cfg ',cfg)
            # load and expand config
            paramMap = self.translator.load_param_map(cfg)['ECON-T']
            pairs = self.translator.pairs_from_cfg(paramMap)

            # read previous values of addresses 
            self.writeCache = self.read_pairs(pairs)
            print('previous values ',self.writeCache)
            # get new default values
            writePairs = self.translator.pairs_from_cfg(paramMap,prevCache=self.writeCache)
            print('new values ',writePairs)
        else:
            print('writing default')
            # read previous values of addresses
            self.writeCache = self.read_pairs(default)
            
            # get new default values 
            writePairs = self.translator.pairs_from_cfg(prevCache=self.writeCache)
        
        # write registers
        print('write registers ')
        self.write_pairs(writePairs)

        return "ECON Configured"

    def read(self, cfg=None):
        """ Read from configs or cache """
        if cfg: return self.__read_fr_cfg(cfg)
        else: return self.__read_fr_cache()

    def read_pairs(self, pairs):
        """ Read addresses in addr:val pairs """
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
        # TODO: make this for multiple cfgs?
        paramMap = self.translator.load_param_map(cfg)['ECON-T']
        pairs = self.translator.pairs_from_cfg(paramMap, self.writeCache)
        print('read pairs ')
        rd_pairs = self.read_pairs(pairs)
        print(rd_pairs)
        # TODO: should translate this into a config
        return rd_pairs

    def __read_fr_cache(self):
        """ Read addresses in write_param cache. """
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
