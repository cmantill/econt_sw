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
        from utils.pll_lock_count import PLLLockCount
        self.nlinks=13
        self.sc = StreamCompare()
        self.lc = LinkCapture()
        self.fc = FastCommands()
        self.tv = TestVectors()
        self.pll = PLLLockCount()

    def configure(self,trigger=True,nWords_input=511, nWords_output=4095, nlinks=13):
        self.fc.configure_fc()
        self.nlinks=nlinks
        self.lc.configure_acquire(["lc-input"],'L1A',nwords=nWords_input,total_length=511,bx=0,verbose=True)
        self.lc.configure_acquire(["lc-ASIC","lc-emulator"],'L1A',nwords=nWords_output,total_length=4095,bx=0,verbose=True)
        self.lc.stop_continous_capture(["lc-input","lc-ASIC","lc-emulator"])
        self.lc.do_continous_capture(["lc-input","lc-ASIC","lc-emulator"])
        self.sc.configure_compare(self.nlinks,trigger)
        return "ready"

    def start_daq(self):
        """ Reset comparison counters"""
        self.sc.reset_counters()
        self.sc.configure_compare(nlinks=self.nlinks,trigger=True)
        return "ready"

    def get_daq_counters(self):
        self.sc.latch_counters()
        err_count = self.sc.read_counters(True)
        return err_count

    def reset_counters(self):
        self.sc.latch_counters()
        self.sc.reset_counters()

    def stop_daq(self,timestamp="0",odir="tmp/",irow=28,frow=32,capture=True):
        """ Latch comparison counters"""
        self.sc.latch_counters()
        self.sc.configure_compare(nlinks=self.nlinks,trigger=False)
        err_count = self.sc.read_counters(True)
        os.system(f'mkdir -p {odir}')
        daq_data = None
        if err_count>0 and capture:
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

    def empty_fifo(self):
        data = self.lc.empty_fifo(["lc-ASIC","lc-emulator","lc-input"])

    def getPLLLockCount(self):
        return self.pll.getCount()

    def resetPLLLockCount(self):
        try: 
            self.pll.reset()
            return "PLL_LOCK_B reset"
        except:
            return "error in PLL_LOCK_B reset"

    def testVectors(self, arg_list=[]):
        #build dictionary of arguments
        #arguments are of type "key:val", where key is dtype, idir, or fname that get passed to tv.configure
        args={}
        allowed_args=['dtype','idir','fname']

        for x in arg_list:
            if not ':' in x:
                return f'ERROR: Bad arguments, missing value for {x}'
            arg,val=x.split(':')
            if arg in allowed_args:
                args[arg]=val
            else:
                return f'ERROR: Unknown argument {arg}'
        print(args)
        self.tv.configure(**args)
        return 'Good Test Vector Config'
