import uhal
import time
import argparse
import numpy

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    uhal.disableLogging();
    #uhal.setLogLevelTo(uhal.LogLevel.DEBUG)
    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")

    io_name_to = "ASIC-IO-IO-to-ECONT-ASIC-IO-blocks-0"
    testvectors_switch_name = "test-vectors-to-ASIC-and-emulator-test-vectors-ipif-switch-mux"
    testvectors_stream_name = "test-vectors-to-ASIC-and-emulator-test-vectors-ipif-stream-mux"
    testvectors_bram_name = "test-vectors-to-ASIC-and-emulator-test-vectors-out-block00-bram-ctrl"
    
    bypass_switch_name = "econt-emulator-bypass-option-expected-outputs-RAM-ipif-switch-mux"
    bypass_stream_name = "econt-emulator-bypass-option-expected-outputs-RAM-ipif-stream-mux"

    input_nlinks = 12

    io_name_from = "ASIC-IO-IO-from-ECONT-ASIC-IO-blocks-0"
    output_nlinks = 13

    # send PRBS
    for l in range(input_nlinks):
        link = "link%i"%l
        dev.getNode(testvectors_switch_name+"."+link+".output_select").write(0x1)
    dev.dispatch()
