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

    # set bypass option
    for l in range(output_nlinks):
        link = "link%i"%l
        dev.getNode(bypass_switch_name+"."+link+".output_select").write(0x1)
    dev.dispatch()

    # link captures
    link_capture_name = "capture-align-compare-ECONT-ASIC-link-capture-link-capture-AXI-0"
    bram_name = "capture-align-compare-ECONT-ASIC-link-capture-link-capture-AXI-0_FIFO"

    link_capture_name_emulator = "capture-align-compare-ECONT-emulator-link-capture-link-capture-AXI-0"
    bram_name_emulator = "capture-align-compare-ECONT-emulator-link-capture-link-capture-AXI-0_FIFO"

    c = dev.getNode("housekeeping-FastControl-fastcontrol-recv-axi-0.counters.link_reset_econt").read();
    dev.dispatch()
    print(c)

    for lcapture in [link_capture_name,link_capture_name_emulator]:
        dev.getNode(lcapture+".global.link_enable").write(0x1fff)
        dev.getNode(lcapture+".global.explicit_resetb").write(0x0)
        time.sleep(0.001)
        dev.getNode(lcapture+".global.explicit_resetb").write(0x1)
        dev.dispatch()
        for l in range(output_nlinks):
            link = "link%i"%l
            dev.getNode(lcapture+"."+link+".align_pattern").write(0b00100100010)
            # dev.getNode(lcapture+"."+link+".L1A_offset_or_BX").write(3554)
            dev.getNode(lcapture+"."+link+".L1A_offset_or_BX").write(0)
            dev.getNode(lcapture+"."+link+".capture_mode_in").write(0x2)
            dev.getNode(lcapture+"."+link+".capture_linkreset_ECONt").write(0x1)
            dev.getNode(lcapture+"."+link+".capture_L1A").write(0x0)
            dev.getNode(lcapture+"."+link+".capture_linkreset_ROCd").write(0x0)
            dev.getNode(lcapture+"."+link+".capture_linkreset_ROCt").write(0x0)
            dev.getNode(lcapture+"."+link+".capture_linkreset_ECONd").write(0x0)
            dev.getNode(lcapture+"."+link+".aquire_length").write(4096)
            #delay_out = dev.getNode(io_name_from+"."+link+".reg3.delay_out").read()
            #dev.dispatch()
            #print('delay out %d %i'%(delay_out,1*(delay_out<0x100)))
            #dev.getNode(lcapture+"."+link+".fifo_latency").write(1*(delay_out<0x100))
            #dev.getNode(lcapture+"."+link+".fifo_latency").write(1)
            dev.dispatch()

    def capture(fifo_latency):
        for l in range(output_nlinks):
            link = "link%i"%l
            dev.getNode(link_capture_name+"."+link+".fifo_latency").write(1)
            dev.getNode(link_capture_name_emulator+"."+link+".fifo_latency").write(fifo_latency)
            dev.dispatch()

        dev.getNode(link_capture_name+".global.aquire").write(0)
        dev.getNode(link_capture_name_emulator+".global.aquire").write(0) 
        dev.dispatch()
        
        dev.getNode(link_capture_name+".global.aquire").write(1)
        dev.getNode(link_capture_name_emulator+".global.aquire").write(1)
        dev.dispatch()
        
        dev.getNode("housekeeping-FastControl-fastcontrol-axi-0.bx_link_reset_econt").write(3550)
        dev.dispatch()
        dev.getNode("housekeeping-FastControl-fastcontrol-axi-0.request.link_reset_econt").write(0x1);
        dev.dispatch()
        
        dev.getNode(link_capture_name+".global.aquire").write(0)
        dev.getNode(link_capture_name_emulator+".global.aquire").write(0)
        dev.dispatch()
        
        c = dev.getNode("housekeeping-FastControl-fastcontrol-recv-axi-0.counters.link_reset_econt").read();
        dev.dispatch()
        print(c)
        
        lcapture = link_capture_name
        asic_i = 0
        for l in range(output_nlinks):
            link = "link%i"%l
            aligned_c = dev.getNode(lcapture+"."+link+".link_aligned_count").read()
            error_c = dev.getNode(lcapture+"."+link+".link_error_count").read()
            aligned = dev.getNode(lcapture+"."+link+".status.link_aligned").read()
            dev.dispatch()
            print('%s %s aligned: %d %d %d'%(lcapture,link, aligned, aligned_c, error_c))

            fifo_occupancy = dev.getNode(lcapture+"."+link+".fifo_occupancy").read()
            dev.dispatch()
            occ = '%d'%fifo_occupancy
            #print(occ)                                                                                                                                                                                                                                                                                                
            if occ>0:
                data = dev.getNode(bram_name+"."+link).readBlock(int(fifo_occupancy))
                dev.dispatch()
                print('fifo occupancy %s %d %i' %(link,fifo_occupancy,len(data)))
                if l==0:
                    for i,d in enumerate(data):
                        if d==0xf922f922:
                            print(i,hex(d))
                            asic_i = i
                            break;
        dev.getNode(lcapture+".global.interrupt_enable").write(0x0)
        dev.dispatch()
        found = False

        lcapture = link_capture_name_emulator
        for l in range(output_nlinks):
            link = "link%i"%l
            aligned_c = dev.getNode(lcapture+"."+link+".link_aligned_count").read()
            error_c = dev.getNode(lcapture+"."+link+".link_error_count").read()
            aligned = dev.getNode(lcapture+"."+link+".status.link_aligned").read()
            dev.dispatch()
            print('%s %s aligned: %d %d %d'%(lcapture,link, aligned, aligned_c, error_c))

            fifo_occupancy = dev.getNode(lcapture+"."+link+".fifo_occupancy").read()
            dev.dispatch()
            occ = '%d'%fifo_occupancy
            #print(occ)
            if occ>0:
                data = dev.getNode(bram_name_emulator+"."+link).readBlock(int(fifo_occupancy))
                dev.dispatch()
                print('fifo occupancy %s %d %i' %(link,fifo_occupancy,len(data)))
                if l==0:
                    for i,d in enumerate(data):
                        #print(hex(d))
                        #print('%02x'%d,hex(d)) 
                        if d==0xf922f922:
                            print(i,hex(d))
                            if i==asic_i:
                                found = True
            dev.getNode(lcapture+"."+link+".aquire").write(0x0)
            dev.getNode(lcapture+"."+link+".explicit_rstb_acquire").write(0x0)
            dev.getNode(lcapture+"."+link+".explicit_rstb_acquire").write(0x1)
            dev.dispatch()

        dev.getNode(lcapture+".global.interrupt_enable").write(0x0)
        dev.dispatch()
        return found
        
    for lat in range(0,15):
        ret = capture(lat)
        if ret:
            print('found!')
            break;

    # set stream compare
    stream_compare_name = "capture-align-compare-compare-outputs-stream-compare-0"
    dev.getNode(stream_compare_name+".control.reset").write(0x1) # start the counters from zero
    time.sleep(0.001)
    dev.getNode(stream_compare_name+".control.latch").write(0x1) 
    dev.dispatch()
    word_count = dev.getNode(stream_compare_name+".word_count").read()
    err_count = dev.getNode(stream_compare_name+".err_count").read()
    dev.dispatch()
    print('word count %d, error count %d'%(word_count,err_count))

    # send a L1A to two capture blocks
    # dev.getNode(stream_compare_name+".trigger").write(0x1)
    # then set the capture blocks to capture when they see a L1A
