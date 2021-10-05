import uhal
import time
import argparse
import numpy
import logging

logging.basicConfig()

"""
PRBS tests using python2 uhal

We set prbs_chk_en and prbs28_en, set up the firmware to send PRBS to the ECON-T emulator and set up the headers using the new registers, then check for errors by looking at prbs_chk_err.

Usage:
   python testing/uhal-prbs.py
"""

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE, NONE",default='NONE')    
    args = parser.parse_args()

    if args.logLevel.find("ERROR")==0:
        uhal.setLogLevelTo(uhal.LogLevel.ERROR)
    elif args.logLevel.find("WARNING")==0:
        uhal.setLogLevelTo(uhal.LogLevel.WARNING)
    elif args.logLevel.find("NOTICE")==0:
        uhal.setLogLevelTo(uhal.LogLevel.NOTICE)
    elif args.logLevel.find("DEBUG")==0:
        uhal.setLogLevelTo(uhal.LogLevel.DEBUG)
    elif args.logLevel.find("INFO")==0:
        uhal.setLogLevelTo(uhal.LogLevel.INFO)
    else:
        uhal.disableLogging()

    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")

    logger = logging.getLogger('prbs')
    logger.setLevel(logging.INFO)
    
    names = {
        'IO': {'to': "ASIC-IO-IO-to-ECONT-ASIC-IO-blocks-0",
               'from': "ASIC-IO-IO-from-ECONT-ASIC-IO-blocks-0"},
        'testvectors': {'switch': "test-vectors-to-ASIC-and-emulator-test-vectors-ipif-switch-mux",
                        'stream': "test-vectors-to-ASIC-and-emulator-test-vectors-ipif-stream-mux",
                        'bram': "test-vectors-to-ASIC-and-emulator-test-vectors-out-block00-bram-ctrl"
                    },
        'bypass': {'switch': "econt-emulator-bypass-option-expected-outputs-RAM-ipif-switch-mux",
                   'stream': "econt-emulator-bypass-option-expected-outputs-RAM-ipif-stream-mux"
               },
        'fc': "housekeeping-FastControl-fastcontrol-axi-0",
        'fc-recv': "housekeeping-FastControl-fastcontrol-recv-axi-0",
        'lc-ASIC': {'lc': "capture-align-compare-ECONT-ASIC-link-capture-link-capture-AXI-0",
                    'fifo': "capture-align-compare-ECONT-ASIC-link-capture-link-capture-AXI-0_FIFO",
                    },
        'lc-emulator': {'lc': "capture-align-compare-ECONT-emulator-link-capture-link-capture-AXI-0",
                        'fifo': "capture-align-compare-ECONT-emulator-link-capture-link-capture-AXI-0_FIFO",
                        },
        'stream_compare': "capture-align-compare-compare-outputs-stream-compare-0",

    }
    input_nlinks = 12
    output_nlinks = 13

    testvectors_settings = {
        "output_select": 0x1, # for PRBS
        "n_idle_words": 255,
        "idle_word": 0xaccccccc,
        "idle_word_BX0": 0x9ccccccc,
        "header_mask": 0xf0000000,
        #"header_mask": 0x00000000, # for 32 bit
        "header": 0xa0000000,
        "header_BX0": 0x90000000,
    }
    
    for l in range(input_nlinks):
        link = "link%i"%l
        for key,value in testvectors_settings.items():
            dev.getNode(names['testvectors']['switch']+"."+link+"."+key).write(value)
            
            dev.getNode(names['testvectors']['stream']+"."+link+".sync_mode").write(0x1)
            dev.getNode(names['testvectors']['stream']+"."+link+".ram_range").write(0x1)
            dev.getNode(names['testvectors']['stream']+"."+link+".force_sync").write(0x0)
        dev.dispatch()
