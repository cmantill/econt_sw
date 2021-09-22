import uhal
import time
import argparse

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
    input_nlinks = 12

    io_name_from = "ASIC-IO-IO-from-ECONT-ASIC-IO-blocks-0"
    output_nlinks = 13

    # send PRBS
    for l in range(input_nlinks):
        link = "link%i"%l
        dev.getNode(testvectors_switch_name+"."+link+".output_select").write(0x1)
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
        link = "link%i"%l
        bit_tr = dev.getNode(io_name_from+"."+link+".reg3.waiting_for_transitions").read()
        delay_ready = dev.getNode(io_name_from+"."+link+".reg3.delay_ready").read()
        dev.dispatch()
        # print("%s: bit_tr %d and delay ready %d"%(link,bit_tr,delay_ready))
        if delay_ready==1:
            print('%s DELAY READY!'%link)

    # setup normal output
    out_brams = []
    for l in range(input_nlinks):
        link = "link%i"%l
        dev.getNode(testvectors_switch_name+"."+link+".output_select").write(0x0)
        dev.getNode(testvectors_switch_name+"."+link+".n_idle_words").write(255)
        dev.getNode(testvectors_switch_name+"."+link+".idle_word").write(0xACCCCCCC)
        dev.getNode(testvectors_switch_name+"."+link+".idle_word_BX0").write(0x9CCCCCCC)
        dev.getNode(testvectors_stream_name+"."+link+".sync_mode").write(1)
        dev.getNode(testvectors_stream_name+"."+link+".ram_range").write(1)
        out_brams.append([None] * 8192)
    dev.dispatch()

    # set zero data with headers
    for l in range(input_nlinks):
        for i,b in enumerate(out_brams[l]):
            if i==0: out_brams[l][i] = 0xa0000000
            else: out_brams[l][i] = 0x90000000
        #out_brams[l][1:] = 0x90000000
        #out_brams[l][0] = 0xa0000000
        link = "%02d"%l
        dev.getNode(testvectors_bram_name.replace('00',link)).writeBlock(out_brams[l])
        
    # send link reset roct
    # this would align the emulator on the ASIC board and the emulator on the tester board simultaneously
    dev.getNode("fastcontrol_axi.request.link_reset_econt").write(0x1);
    dev.dispatch()
