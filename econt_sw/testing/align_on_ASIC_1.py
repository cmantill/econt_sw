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

    # setup from-IO
    for l in range(output_nlinks):
        link = "link%i"%l
        dev.getNode(io_name_from+"."+link+".reg0.tristate_IOBUF").write(0x0)
        dev.getNode(io_name_from+"."+link+".reg0.bypass_IOBUF").write(0x0)
        dev.getNode(io_name_from+"."+link+".reg0.invert").write(0x0)

        dev.getNode(io_name_from+"."+link+".reg0.reset_link").write(0x0)
        dev.getNode(io_name_from+"."+link+".reg0.reset_counters").write(0x1)
        dev.getNode(io_name_from+"."+link+".reg0.delay_mode").write(0x0)
        dev.dispatch()

    dev.getNode(io_name_from+".global.global_rstb_links").write(0x1)
    dev.dispatch()

    # align to-IO
    for l in range(input_nlinks):
        link = "link%i"%l
        dev.getNode(io_name_to+"."+link+".reg0.tristate_IOBUF").write(0x0)
        dev.getNode(io_name_to+"."+link+".reg0.bypass_IOBUF").write(0x0)
        dev.getNode(io_name_to+"."+link+".reg0.invert").write(0x0)

        dev.getNode(io_name_to+"."+link+".reg0.reset_link").write(0x0)
        dev.getNode(io_name_to+"."+link+".reg0.reset_counters").write(0x1)
        dev.getNode(io_name_to+"."+link+".reg0.delay_mode").write(0x1)
        dev.dispatch()

    dev.getNode(io_name_to+".global.global_rstb_links").write(0x1)
    dev.dispatch()

    # check that IO is aligned
    for l in range(input_nlinks):
        while True:
            link = "link%i"%l
            bit_tr = dev.getNode(io_name_to+"."+link+".reg3.waiting_for_transitions").read()
            delay_ready = dev.getNode(io_name_to+"."+link+".reg3.delay_ready").read()
            dev.dispatch()
            print("%s: bit_tr %d and delay ready %d"%(link,bit_tr,delay_ready))
            if delay_ready==1:
                break;    

    reset_roc = dev.getNode("fast-command-fastcontrol-recv-axi-0.counters.link_reset_roct").read()
    dev.dispatch()
    reset_econt = dev.getNode("fast-command-fastcontrol-recv-axi-0.counters.link_reset_econt").read()
    dev.dispatch()
    print('Initial reset roct counters %d'%reset_roc)
    print('Initial reset econt counters %d'%reset_econt)

    # check that PRBS is coming
    dev.getNode(input_link_capture_name+".global.link_enable").write(0x1fff)
    dev.getNode(input_link_capture_name+".global.explicit_resetb").write(0x0)
    time.sleep(0.001)
    dev.getNode(input_link_capture_name+".global.explicit_resetb").write(0x1)
    dev.dispatch() 
    for l in range(input_nlinks):
        link = "link%i"%l
        dev.getNode(input_link_capture_name+"."+link+".align_pattern").write(0b00100100010)
        dev.getNode(input_link_capture_name+"."+link+".L1A_offset_or_BX").write(3500)
        dev.getNode(input_link_capture_name+"."+link+".capture_mode_in").write(0x1)
        dev.getNode(input_link_capture_name+"."+link+".aquire_length").write(0x1000)
        dev.getNode(input_link_capture_name+"."+link+".fifo_latency").write(0x0)
        dev.dispatch()
    dev.getNode(input_link_capture_name+".global.aquire").write(0)
    dev.getNode(input_link_capture_name+".global.aquire").write(1)
    dev.dispatch()
    time.sleep(0.001)
    dev.getNode(input_link_capture_name+".global.aquire").write(0)
    dev.dispatch()

    for l in range(input_nlinks):
        link = "link%i"%l
        aligned_c = dev.getNode(input_link_capture_name+"."+link+".link_aligned_count").read()
        error_c = dev.getNode(input_link_capture_name+"."+link+".link_error_count").read()
        aligned = dev.getNode(input_link_capture_name+"."+link+".status.link_aligned").read()
        dev.dispatch()
        print('%s %s %d %d %d'%(input_link_capture_name,link, aligned, aligned_c, error_c))

        fifo_occupancy = dev.getNode(input_link_capture_name+"."+link+".fifo_occupancy").read()
        dev.dispatch()
        if fifo_occupancy>0:
            data = dev.getNode(input_bram_name+"."+link).readBlock(int(fifo_occupancy))
            dev.dispatch()
            print('fifo occupancy %s %d %i' %(link,fifo_occupancy,len(data)))
            if l==0:
                print(link)
                print([hex(d) for i,d in enumerate(data) if i<15])
        dev.getNode(input_link_capture_name+"."+link+".aquire").write(0x0)
        dev.getNode(input_link_capture_name+"."+link+".explicit_rstb_acquire").write(0x0)
        dev.getNode(input_link_capture_name+"."+link+".explicit_rstb_acquire").write(0x1)
        dev.dispatch()
    dev.getNode(input_link_capture_name+".global.interrupt_enable").write(0x0)
    dev.dispatch()


    # setup link capture to capture on roct?
