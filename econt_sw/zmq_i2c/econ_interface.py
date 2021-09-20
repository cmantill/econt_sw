from translator import Translator
from econ_i2c import econ_i2c
import yaml
import logging
import sys

def _init_logger():
    logger = logging.getLogger('i2c')
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(  
        '%(created)f:%(levelname)s:%(name)s:%(module)s:%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class econ_interface():
    """ Base class for interfacing with ECON at i2c register level """

    def __init__(self, addr=0x20):
        _init_logger()
        self._logger = logging.getLogger('i2c')
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
            self._logger.info('Successfully loaded custom configuration pairs')
        else:
            # read previous values of addresses
            self.writeCache = self.read_pairs(default)
            
            # get new default values 
            writePairs = self.translator.pairs_from_cfg(prevCache=self.writeCache)
            self._logger.info('Successfully loaded default configuration pairs')
        
        # write registers
        self.write_pairs(writePairs)
        return "i2c: ECON Configured"

    def compare(self):
        """ Read from cache and compare """
        cache_pairs = self.writeCache
        read_pairs = self.__read_fr_cache()
        cache_unmatch = {k: cache_pairs[k] for k in cache_pairs if k in read_pairs and cache_pairs[k] != read_pairs[k]}
        read_unmatch = {k: read_pairs[k] for k in cache_unmatch}
        if len(cache_unmatch.keys())>0:
             self._logger.warning('Not all values read match cache')
             self._logger.warning('Cache pairs %s',self.translator.cfg_from_pairs(cache_unmatch))
             self._logger.warning('Read pairs %s',self.translator.cfg_from_pairs(read_unmatch))
        return read_unmatch

    def read(self, cfg=None):
        """ Read from configs or cache """
        # print('read from configs or cache ',cfg)
        if cfg: 
            return self.__read_fr_cfg(cfg)
        else: 
            return self.__read_fr_cache()

    def read_pairs(self, pairs):
        """ Read addresses in addr:[val,size_byte] pairs """
        pairs_read = {}
        for addr,vals in pairs.items():
            size_byte = vals[1]
            pairs_read[addr] = [self.__read_I2C_reg(addr, size_byte),size_byte]
        self._logger.info('Successfully read addr:[val,size_byte] pairs')
        self._logger.debug('Pairs read: %s', pairs_read)
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
        rd_pairs = self.read_pairs(pairs)
        cfgRead = self.translator.cfg_from_pairs(rd_pairs,cfg)
        self._logger.info('Successfully read addresses')
        return cfgRead

    def __read_fr_cache(self):
        """ Read addresses in write_param cache. """
        rd_pairs = self.read_pairs(self.writeCache)
        return rd_pairs

    def __read_I2C_reg(self, addr, size_byte):
        """ Read byte from register. """
        try: 
            return self.i2c.read(self.i2c_addr, addr, size_byte)
        except IOError as e:
            self._logger.error('IOError in read. Attempting re-read.')
            self.__read_I2C_reg(addr, size_byte)
        except Exception: raise     # For all other errors reset the I2C state machine and the chip.

    def __set_I2C_reg(self, addr, val):
        """
        Write byte to register.
        """
        try:
            return self.i2c.write(self.i2c_addr, addr, val)
        except IOError as e:
            self._logger.error('IOError in write. Attempting re-write.')
            self.__set_I2C_reg(addr, val)
        except Exception: raise  # For all other errors reset the I2C state machine and the chip.
