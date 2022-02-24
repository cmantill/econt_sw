import yaml
import logging
import sys

def _init_logger():
    logger = logging.getLogger('hexactrl')
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(created)f:%(levelname)s:%(name)s:%(module)s:%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class hexactrl_interface():
    """ Base class for interfacing with hexacontroller via uhal """

    def __init__(self, addr=0x20, i2c=1):
        _init_logger()
        self._logger = logging.getLogger('hexactrl')


    def init(self):
        from align_on_tester import init as init_step
        init_step()
        
