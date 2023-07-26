
connection_filename = "file:///opt/cms-hgcal-firmware/hgc-test-systems/active/uHAL_xml/connections.xml" 
deviceName = "TOP"

names = {
    'IO': {'to': "ASIC-IO-IO-to-ECONT-ASIC-IO-blocks-0",
           'from': "ASIC-IO-IO-from-ECONT-ASIC-IO-blocks-0"},
    'testvectors': {'switch': "test-vectors-to-ASIC-and-emulator-test-vectors-ipif-switch-mux",
                    'stream': "test-vectors-to-ASIC-and-emulator-test-vectors-ipif-stream-mux",
                    'bram': "test-vectors-to-ASIC-and-emulator-test-vectors-out-block00-bram-ctrl",
                },
    'bypass': {'switch': "econt-emulator-bypass-option-expected-outputs-RAM-ipif-switch-mux",
               'stream': "econt-emulator-bypass-option-expected-outputs-RAM-ipif-stream-mux",
               'bram': "econt-emulator-bypass-option-expected-outputs-RAM-out-block00-bram-ctrl"
           },
    'fc': "housekeeping-FastControl-fastcontrol-axi-0",
    'fc-recv': "housekeeping-FastControl-fastcontrol-recv-axi-0",
    'lc-ASIC': {'lc': "capture-align-compare-ECONT-ASIC-link-capture-link-capture-AXI-0",
                'fifo': "capture-align-compare-ECONT-ASIC-link-capture-link-capture-AXI-0_FIFO",
            },
    'lc-emulator': {'lc': "capture-align-compare-ECONT-emulator-link-capture-link-capture-AXI-0",
                    'fifo': "capture-align-compare-ECONT-emulator-link-capture-link-capture-AXI-0_FIFO",
            },
    'lc-input': {'lc': "capture-align-compare-input-link-capture-link-capture-AXI-0",
                 'fifo': "capture-align-compare-input-link-capture-link-capture-AXI-0_FIFO",
             },
    'stream_compare': "capture-align-compare-compare-outputs-stream-compare-0",    
    'delay': "ECONT-Emulator-axis-delay-0",
    'fudge': "ASIC-IO-I2C-I2C-fudge-0",
    
    'ASIC-IO': {'to': "IO-to-ECONT-IO-blocks-0",
                'from': "IO-from-ECONT-IO-blocks-0",
            },
    'ASIC-lc-input': {'lc': "IO-to-ECONT-input-link-capture-link-capture-AXI-0",
                      'fifo': "IO-to-ECONT-input-link-capture-link-capture-AXI-0_FIFO",
                  },
    'ASIC-lc-output': {'lc': "IO-from-ECONT-output-link-capture-link-capture-AXI-0",
                       'fifo': "IO-from-ECONT-output-link-capture-link-capture-AXI-0_FIFO",
                   },
    'ASIC-fc-recv': "fast-command-fastcontrol-recv-axi-0",
}
input_nlinks = 12
output_nlinks = 13

def set_logLevel(logLevel=""):
    import uhal
    if logLevel.find("ERROR")==0:
        uhal.setLogLevelTo(uhal.LogLevel.ERROR)
    elif logLevel.find("WARNING")==0:
        uhal.setLogLevelTo(uhal.LogLevel.WARNING)
    elif logLevel.find("NOTICE")==0:
        uhal.setLogLevelTo(uhal.LogLevel.NOTICE)
    elif logLevel.find("DEBUG")==0:
        uhal.setLogLevelTo(uhal.LogLevel.DEBUG)
    elif logLevel.find("INFO")==0:
        uhal.setLogLevelTo(uhal.LogLevel.INFO)
    else:
        uhal.disableLogging()
