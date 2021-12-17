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

def print_nested(d, read_str, prefix=''):
    for k, v in d.items():
        if isinstance(v, dict):
            print_nested(v, read_str, '{}{}_'.format(prefix, k))
        else:
            read_str['{}{}'.format(prefix, k,)] = v

def print_keys(d, read_keys, prefix=''):
    for k, v in d.items():
        if isinstance(v, dict):
            print_keys(v, read_keys, '{}{}_'.format(prefix, k))
        else:
            read_keys.append('{}{}'.format(prefix, k))
            
class econ_interface():
    """ Base class for interfacing with ECON at i2c register level """

    def __init__(self, addr=0x20, i2c=1):
        _init_logger()
        self._logger = logging.getLogger('i2c')
        self.i2c = econ_i2c(i2c)
        self.translator = Translator('ECON-T')
        self.i2c_addr = addr
        self.writeCache = {}

    def reset_cache(self):
        """ Reset cache """
        self.writeCache = {}

    def configure(self, cfg=None):
        """ Configure ECON i2c with RW registers and return when finished """
        # read all default register:[address,size_byte] pairs into a default dict
        default_pairs = self.translator.pairs_from_cfg(prevCache=self.writeCache,allowed=['RW'])

        if cfg:
            # load and expand config
            paramMap = self.translator.load_param_map(cfg)
            try:
                paramMap = paramMap['ECON-T']
            except:
                self._logger.warning('No filename for config')
                return "i2c: ECON Not Configured"

            pairs = self.translator.pairs_from_cfg(paramMap,allowed=['RW'])

            # read previous values of addresses 
            self.writeCache = self.read_pairs(pairs)

            # get new values
            writePairs = self.translator.pairs_from_cfg(paramMap,prevCache=self.writeCache,allowed=['RW'])
            self._logger.info('Loaded custom configuration pairs')
        else:
            # read previous values of addresses in register:address dict
            self.writeCache = self.read_pairs(default_pairs)

            # get new values 
            writePairs = self.translator.pairs_from_cfg(prevCache=self.writeCache,allowed=['RW'])
            self._logger.info('Loaded default configuration pairs')

        # update cache with new written pairs
        self.writeCache = self.translator.convert_pairs(writePairs,direction='from')

        # write registers (only write RW registers)
        self.write_pairs(writePairs)
        self._logger.debug('Written addr-register pairs: ',writePairs)

        return "i2c: ECON Configured"

    def compare(self,access='RW'):
        """ Read and compare. For RW read from cache, for RO read from default map."""
        unmatched_keys = ""
        if access=='RW':
            cache_pairs = self.writeCache
            read_pairs = self.__read_fr_cache()
        else:
            default_pairs = self.translator.pairs_from_cfg(prevCache={},allowed=['RO'])
            cache_pairs = self.translator.convert_pairs(default_pairs,direction='from')
            read_pairs = self.read_pairs(default_pairs)

        cache_unmatch = {k: cache_pairs[k] for k in cache_pairs if k in read_pairs and cache_pairs[k] != read_pairs[k]}
        read_unmatch = {k: read_pairs[k] for k in cache_unmatch}
        if len(cache_unmatch.keys())>0:
            self._logger.warning('Not all values read match cache for %s'%access)
            cache_values = {}; read_values = {};
            print_nested(self.translator.cfg_from_pairs(cache_unmatch),cache_values)
            print_nested(self.translator.cfg_from_pairs(read_unmatch),read_values)
            self._logger.debug('Unmatched registers: ')
            for key in cache_values.keys():
                self._logger.debug('{}, Wrote: {}, Read: {}'.format(key,cache_values[key],read_values[key]))
            unmatched_keys = ",".join(map(str, cache_values.keys()))
        return unmatched_keys

    def read(self, cfg=None):
        """ Read from configs or cache """
        if cfg:
            self._logger.debug('Reading config ',cfg)
            return self.__read_fr_cfg(cfg)
        else: 
            self._logger.debug('Reading from cache')
            return self.__read_fr_cache()

    def read_pairs(self, pairs):
        """ Read addresses in addr:[[values],size_byte] pairs """
        pairs_read = {}
        for addr,vals in pairs.items():
            size_byte = vals[1]
            pairs_read[addr] = [self.__read_I2C_reg(addr, size_byte),size_byte]
        self._logger.debug('Successfully read addr:[val,size_byte] pairs')
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
        paramMap = self.translator.load_param_map(cfg)
        try:
            paramMap = paramMap['ECON-T']
        except:
            self._logger.warning('No filename for reading config')
            return {}
        pairs = self.translator.pairs_from_cfg(paramMap, self.writeCache)
        rd_pairs = self.read_pairs(pairs)
        cfgRead = self.translator.cfg_from_pairs(rd_pairs,cfg)
        self._logger.info('Read addresses from config')
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
        """ Write byte to register. """
        try:
            return self.i2c.write(self.i2c_addr, addr, val)
        except IOError as e:
            self._logger.error('IOError in write. Attempting re-write.')
            self.__set_I2C_reg(addr, val)
        except Exception: raise  # For all other errors reset the I2C state machine and the chip.
