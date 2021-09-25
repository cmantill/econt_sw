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

    # set to-IO
    for l in range(input_nlinks):
        link = "link%i"%l
        dev.getNode(io_name_to+"."+link+".reg0.tristate_IOBUF").write(0x0)
        dev.getNode(io_name_to+"."+link+".reg0.bypass_IOBUF").write(0x0)
        dev.getNode(io_name_to+"."+link+".reg0.invert").write(0x0)
        dev.getNode(io_name_to+"."+link+".reg0.reset_link").write(0x0)
        dev.getNode(io_name_to+"."+link+".reg0.reset_counters").write(0x1)
        dev.getNode(io_name_to+"."+link+".reg0.delay_mode").write(0x0)
    dev.getNode(io_name_to+".global.global_rstb_links").write(0x1)
    dev.dispatch()

    # set from-IO delay mode
    for l in range(output_nlinks):
        link = "link%i"%l
        dev.getNode(io_name_from+"."+link+".reg0.tristate_IOBUF").write(0x0)
        dev.getNode(io_name_from+"."+link+".reg0.bypass_IOBUF").write(0x0)
        dev.getNode(io_name_from+"."+link+".reg0.invert").write(0x0)
        dev.getNode(io_name_from+"."+link+".reg0.reset_link").write(0x0)
        dev.getNode(io_name_from+"."+link+".reg0.reset_counters").write(0x1)
        dev.getNode(io_name_from+"."+link+".reg0.delay_mode").write(0x1)
    dev.getNode(io_name_from+".global.global_rstb_links").write(0x1)
    dev.dispatch()

    # check from-IO is aligned
    for l in range(output_nlinks):
        while True:
            link = "link%i"%l
            bit_tr = dev.getNode(io_name_from+"."+link+".reg3.waiting_for_transitions").read()
            delay_ready = dev.getNode(io_name_from+"."+link+".reg3.delay_ready").read()
            dev.dispatch()
            print("%s: bit_tr %d and delay ready %d"%(link,bit_tr,delay_ready))
            if delay_ready==1:
                break
