import yaml
import logging
import sys
import os
import numpy as np

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
        from utils.test_vectors import TestVectors
        self.sc = StreamCompare()
        self.lc = LinkCapture()
        self.fc = FastCommands()
        self.tv = TestVectors()

    def configure(self,trigger=True):
        self.fc.configure_fc()
        self.lc.configure_acquire(["lc-input"],'L1A',511,0,verbose=True)
        self.lc.configure_acquire(["lc-ASIC","lc-emulator"],'L1A',4095,0,verbose=True)
        self.lc.do_capture(["lc-input","lc-ASIC","lc-emulator"],verbose=True)
        self.sc.configure_compare(13,trigger)
        return "ready"

    def reset_counters(self):
        """ Reset comparison counters"""
        self.sc.reset_counters()
        return "ready"

    def latch_counters(self,timestamp="0",odir="tmp/",irow=28,frow=32):
        """ Latch comparison counters"""
        self.sc.latch_counters()
        err_count = self.sc.read_counters(False)
        os.system(f'mkdir -p {odir}')
        daq_data = None
        if err_count>0:
            first_rows = {}
            data = self.lc.get_captured_data(["lc-ASIC","lc-emulator"],4095,False)
            data['lc-input'] = self.lc.get_captured_data(["lc-input"],511,False)['lc-input']
            for lcapture in data.keys():
                filename = f"{odir}/{lcapture}_{timestamp}.csv"
                self.tv.save_testvector(filename,data[lcapture])
                first_rows[lcapture] = self.tv.fixed_hex(data[lcapture],8)[irow:frow]
            daq_data = np.vstack(
                (first_rows['lc-ASIC'], 
                 first_rows['lc-emulator'],
                 np.pad(first_rows['lc-input'], [(0, 0), (0, 1)])
             )
            )
        return err_count,daq_data

    
