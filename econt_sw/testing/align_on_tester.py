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
            if delay_ready==1:
                break

    # setup normal output
    out_brams = []
    for l in range(input_nlinks):
        link = "link%i"%l
        dev.getNode(testvectors_switch_name+"."+link+".output_select").write(0x0)
        dev.getNode(testvectors_switch_name+"."+link+".n_idle_words").write(255)
        #dev.getNode(testvectors_switch_name+"."+link+".n_idle_words").write(0)
        dev.getNode(testvectors_switch_name+"."+link+".idle_word").write(0xaccccccc)
        dev.getNode(testvectors_switch_name+"."+link+".idle_word_BX0").write(0x9ccccccc)
        #dev.getNode(testvectors_switch_name+"."+link+".idle_word_BX0").write(0xabcd1234)
        dev.getNode(testvectors_switch_name+"."+link+".header_mask").write(0xf0000000)
        dev.getNode(testvectors_switch_name+"."+link+".header").write(0xa0000000)
        dev.getNode(testvectors_switch_name+"."+link+".header_BX0").write(0x90000000)
        #out_brams.append([None] * 2048)
        out_brams.append([None] * 4096)
        dev.dispatch()

    for l in range(input_nlinks):
        dev.getNode(testvectors_stream_name+"."+link+".sync_mode").write(0x1)
        dev.getNode(testvectors_stream_name+"."+link+".ram_range").write(0x1)
    dev.dispatch()
    
    # checking settings
    for l in range(input_nlinks):
        osel = dev.getNode(testvectors_switch_name+"."+link+".output_select").read()
        nwords = dev.getNode(testvectors_switch_name+"."+link+".n_idle_words").read()
        idle = dev.getNode(testvectors_switch_name+"."+link+".idle_word").read()
        idlebx0 =  dev.getNode(testvectors_switch_name+"."+link+".idle_word_BX0").read()
        header_mask = dev.getNode(testvectors_switch_name+"."+link+".header_mask").read()
        header = dev.getNode(testvectors_switch_name+"."+link+".header").read()
        header_BX0 = dev.getNode(testvectors_switch_name+"."+link+".header_BX0").read()
        dev.dispatch()
        if l==0:
            print('osel %d, nwords %d, idle %02x, idlebx0 %02x, header_mask %02x, header %02x, header_BX0 %02x'%(osel,nwords,idle,idlebx0,header_mask,header,header_BX0))
        sync = dev.getNode(testvectors_stream_name+"."+link+".sync_mode").read()
        ram = dev.getNode(testvectors_stream_name+"."+link+".ram_range").read()
        force_sync =  dev.getNode(testvectors_stream_name+"."+link+".force_sync").read()
        dev.dispatch()
        #print('sync %d, ram %d, force_sync %d '%(sync,ram,force_sync))

    # set zero data with headers
    for l in range(input_nlinks):
        for i,b in enumerate(out_brams[l]):
            if i==0: out_brams[l][i] = 0x90000000
            else: 
                out_brams[l][i] = 0xa0000000
                #out_brams[l][i] = 0xa0000000+i
        link = "%02d"%l
        #if l==0:
        #    for i in out_brams[l]:
        #        print(hex(i))
        #print(hex(out_brams[l][0]),hex(out_brams[l][1]))
        dev.getNode(testvectors_bram_name.replace('00',link)).writeBlock(out_brams[l])
        dev.dispatch()
        time.sleep(0.001)

    # set bypass option                                                                                                                              
    for l in range(output_nlinks):
        link = "link%i"%l
        dev.getNode(bypass_switch_name+"."+link+".output_select").write(0x1)
    dev.dispatch()


    # send link reset roct
    # this would align the emulator on the ASIC board and the emulator on the tester board simultaneously
    dev.getNode("fastcontrol_axi.command.enable_fast_ctrl_stream").write(0x1);
    dev.getNode("fastcontrol_axi.command.enable_orbit_sync").write(0x1);

    dev.getNode("fastcontrol_axi.bx_link_reset_roct").write(3500)
    dev.getNode("fastcontrol_axi.bx_link_reset_rocd").write(3501)
    dev.getNode("fastcontrol_axi.bx_link_reset_econt").write(3502)
    dev.getNode("fastcontrol_axi.bx_link_reset_econd").write(3503)
    dev.getNode("fastcontrol_axi.request.link_reset_roct").write(0x1);
    dev.dispatch()

    # link capture
    link_capture_name = "capture-align-compare-ECONT-ASIC-link-capture-link-capture-AXI-0"
    bram_name = "capture-align-compare-ECONT-ASIC-link-capture-link-capture-AXI-0_FIFO"

    link_capture_name_emulator = "capture-align-compare-ECONT-emulator-link-capture-link-capture-AXI-0"
    bram_name_emulator = "capture-align-compare-ECONT-emulator-link-capture-link-capture-AXI-0_FIFO"

    c = dev.getNode("fastcontrol_recv_axi.counters.link_reset_econt").read();
    dev.dispatch()
    #print(c)

    for lcapture in [link_capture_name,link_capture_name_emulator]:
        dev.getNode(lcapture+".global.link_enable").write(0x1fff)
        dev.getNode(lcapture+".global.explicit_resetb").write(0x0)
        time.sleep(0.001)
        dev.getNode(lcapture+".global.explicit_resetb").write(0x1)
        dev.dispatch()
        for l in range(output_nlinks):
            link = "link%i"%l
            dev.getNode(lcapture+"."+link+".align_pattern").write(0b00100100010)
            dev.getNode(lcapture+"."+link+".L1A_offset_or_BX").write(3554)
            dev.getNode(lcapture+"."+link+".capture_mode_in").write(0x1)
            dev.getNode(lcapture+"."+link+".aquire_length").write(4096)
            #delay_out = dev.getNode(io_name_from+"."+link+".reg3.delay_out").read()
            #dev.dispatch()
            #print('delay out %d %i'%(delay_out,1*(delay_out<0x100)))
            #dev.getNode(lcapture+"."+link+".fifo_latency").write(1*(delay_out<0x100))
            #dev.getNode(lcapture+"."+link+".fifo_latency").write(1)
            dev.dispatch()

    for l in range(output_nlinks):
        link = "link%i"%l
        dev.getNode(link_capture_name_emulator+"."+link+".fifo_latency").write(0)
        dev.getNode(link_capture_name+"."+link+".fifo_latency").write(1)
    dev.dispatch()

    dev.getNode(link_capture_name+".global.aquire").write(0)
    dev.getNode(link_capture_name_emulator+".global.aquire").write(0) 
    dev.dispatch()

    dev.getNode("fastcontrol_axi.bx_link_reset_econt").write(3555)
    dev.dispatch()

    dev.getNode(link_capture_name+".global.aquire").write(1)
    dev.getNode(link_capture_name_emulator+".global.aquire").write(1)
    dev.getNode("fastcontrol_axi.request.link_reset_econt").write(0x1);
    dev.dispatch()

    dev.getNode(link_capture_name+".global.aquire").write(0)
    dev.getNode(link_capture_name_emulator+".global.aquire").write(0)
    dev.dispatch()

    c = dev.getNode("fastcontrol_recv_axi.counters.link_reset_econt").read();
    dev.dispatch()
    # print(c)

    bram_names = [bram_name, bram_name_emulator]
    print(bram_names)
    for c,lcapture in enumerate([link_capture_name,link_capture_name_emulator]):
        print(lcapture)
        for l in range(output_nlinks):
            link = "link%i"%l
            aligned_c = dev.getNode(link_capture_name+"."+link+".link_aligned_count").read()
            error_c = dev.getNode(link_capture_name+"."+link+".link_error_count").read()
            aligned = dev.getNode(link_capture_name+"."+link+".status.link_aligned").read()
            dev.dispatch()
            # print('%s %s %d %d %d'%(lcapture,link, aligned, aligned_c, error_c))

            fifo_occupancy = dev.getNode(lcapture+"."+link+".fifo_occupancy").read()
            dev.dispatch()
            occ = '%d'%fifo_occupancy
            #print(occ)
            if occ>0:
                data = dev.getNode(bram_names[c]+"."+link).readBlock(int(fifo_occupancy))
                dev.dispatch()
                #print('fifo occupancy %s %d %i' %(link,fifo_occupancy,len(data)))
                if l==0:
                    for i,d in enumerate(data):
                        #print(hex(d))
                        print('%02x'%d,hex(d)) 
                        if d==0xf922f922:
                            print(i,d)
            dev.getNode(lcapture+"."+link+".aquire").write(0x0)
            dev.getNode(lcapture+"."+link+".explicit_rstb_acquire").write(0x0)
            dev.getNode(lcapture+"."+link+".explicit_rstb_acquire").write(0x1)
            dev.dispatch()

    dev.getNode(link_capture_name+".global.interrupt_enable").write(0x0)
    dev.getNode(link_capture_name_emulator+".global.interrupt_enable").write(0x0)
    dev.dispatch()
