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
    io_name_from = "ASIC-IO-IO-from-ECONT-ASIC-IO-blocks-0"

    testvectors_switch_name = "test-vectors-to-ASIC-and-emulator-test-vectors-ipif-switch-mux"
    testvectors_stream_name = "test-vectors-to-ASIC-and-emulator-test-vectors-ipif-stream-mux"
    testvectors_bram_name = "test-vectors-to-ASIC-and-emulator-test-vectors-out-block00-bram-ctrl"
    
    bypass_switch_name = "econt-emulator-bypass-option-expected-outputs-RAM-ipif-switch-mux"
    bypass_stream_name = "econt-emulator-bypass-option-expected-outputs-RAM-ipif-stream-mux"

    input_nlinks = 12
    output_nlinks = 13
    
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
        if l==0:
            print('sync %d, ram %d, force_sync %d '%(sync,ram,force_sync))

    # set zero data with headers
    for l in range(input_nlinks):
        for i,b in enumerate(out_brams[l]):
            if i==0: out_brams[l][i] = 0x90000000
            else:
                out_brams[l][i] = 0xa0000000
                #out_brams[l][i] = 0xa0000000+i
        link = "%02d"%l
        dev.getNode(testvectors_bram_name.replace('00',link)).writeBlock(out_brams[l])
        dev.dispatch()
        time.sleep(0.001)
        
    # send link reset roct
    # this would align the emulator on the ASIC board and the emulator on the tester board simultaneously
    dev.getNode("housekeeping-FastControl-fastcontrol-axi-0.command.enable_fast_ctrl_stream").write(0x1);
    dev.getNode("housekeeping-FastControl-fastcontrol-axi-0.command.enable_orbit_sync").write(0x1);
    
    dev.getNode("housekeeping-FastControl-fastcontrol-axi-0.bx_link_reset_roct").write(3500)
    dev.getNode("housekeeping-FastControl-fastcontrol-axi-0.bx_link_reset_rocd").write(3501)
    dev.getNode("housekeeping-FastControl-fastcontrol-axi-0.bx_link_reset_econt").write(3502)
    dev.getNode("housekeeping-FastControl-fastcontrol-axi-0.bx_link_reset_econd").write(3503)
    dev.getNode("housekeeping-FastControl-fastcontrol-axi-0.request.link_reset_roct").write(0x1);
    dev.dispatch()
