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

    def __init__(self):
        _init_logger()
        self._logger = logging.getLogger('hexactrl')
        from utils.stream_compare import StreamCompare
        from utils.link_capture import LinkCapture
        from utils.fast_command import FastCommands
        self.sc = StreamCompare()
        self.lc = LinkCapture()
        self.fc = FastCommands()

    def configure(self,trigger=True):
        self.fc.configure_fc()
        self.lc.configure_acquire(["lc-input"],'L1A',511,0,verbose=True)
        self.lc.configure_acquire(["lc-ASIC","lc-emulator"],'L1A',4095,0,verbose=True)
        self.lc.do_capture(["lc-input","lc-ASIC","lc-emulator"],verbose=True)
        self.sc.configure_compare(13,trigger)
        return "ready"

    def reset(self):
        """ Reset comparison counters"""
        self.sc.reset_counters()
        return "ready"

    def latch(self):
        """ Latch comparison counters"""
        self.sc.latch_counters()
        err_count = self.sc.read_counters(False)
        if err_count>0:
            data = self.lc.get_captured_data(["lc-input"],511,False)
            data = self.lc.get_captured_data(["lc-ASIC","lc-emulator"],4095,False)
        return f"{err_count}"

    
