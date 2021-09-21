import uhal
import time
import argparse

"""
To be run on ASIC.
"""

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    uhal.disableLogging();
    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")

    io_name_to = "IO-to-ECONT-IO-blocks-0"
    input_link_capture_name="IO-to-ECONT-input-link-capture-link-capture-AXI-0"
    input_bram_name="IO-to-ECONT-input-link-capture-link-capture-AXI-0_FIFO"
    input_nlinks = 12

    io_name_from = "IO-from-ECONT-IO-blocks-0"
    output_link_capture_name="IO-from-ECONT-output-link-capture-link-capture-AXI-0"
    output_bram_name="IO-from-ECONT-output-link-capture-link-capture-AXI-0_FIFO"
    output_nlinks = 13

    # align to-IO
    for l in range(input_nlinks):
        link = "link%i"%l
        dev.getNode(io_name_to+"."+link+".reg0.tristate_IOBUF").write(0x0)
        dev.getNode(io_name_to+"."+link+".reg0.bypass_IOBUF").write(0x0)
        dev.getNode(io_name_to+"."+link+".reg0.invert").write(0x0)

        dev.getNode(io_name_to+"."+link+".reg0.reset_link").write(0x0)
        dev.getNode(io_name_to+"."+link+".reg0.reset_counters").write(0x1)
        dev.getNode(io_name_to+"."+link+".reg0.delay_mode").write(0x1)

    dev.getNode(io_name_to+".global.global_rstb_links").write(0x1)
    dev.dispatch()

    # check that IO is aligned
    for l in range(input_nlinks):
        link = "link%i"%l
        while True:
            bit_tr = dev.getNode(io_name_to+"."+link+".reg3.waiting_for_transitions").read()
            delay_ready = dev.getNode(io_name_to+"."+link+".reg3.delay_ready").read()
            dev.dispatch()
            # print("%s: bit_tr %d and delay ready %d"%(link,bit_tr,delay_ready))
            if delay_ready==1:
                print('%s DELAY READY!'%link)
                break;    
