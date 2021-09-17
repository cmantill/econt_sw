import uhal

if __name__ == "__main__":

    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")

    for link in range(12):
        dev.getNode("IO-to-ECONT-IO-blocks-0.link%i.reg0.tristate_IOBUF"%link).write(0x0)
        dev.getNode("IO-to-ECONT-IO-blocks-0.link%i.reg0.invert"%link).write(0x0)

        dev.getNode("IO-to-ECONT-IO-blocks-0.link%i.reg0.reset_link"%link).write(0x0)
        dev.getNode("IO-to-ECONT-IO-blocks-0.link%i.reg0.reset_counters"%link).write(0x1)
        dev.getNode("IO-to-ECONT-IO-blocks-0.link%i.reg0.delay_mode"%link).write(0x1)

    dev.getNode("IO-to-ECONT-IO-blocks-0.global.global_rstb_links").write(0x1)
    dev.dispatch()

    for link in range(12):
        #while True:
        bit_tr = dev.getNode("IO-to-ECONT-IO-blocks-0.link%i.reg3.waiting_for_transitions"%link).read()
        delay_ready = dev.getNode("IO-to-ECONT-IO-blocks-0.link%i.reg3.delay_ready"%link).read()
        dev.dispatch()
        print("link %i: bit_tr %d and delay ready %d"%(link,bit_tr,delay_ready))
        if delay_ready==1:
            print('DELAY READY!')
            #break;    

    # do a link capture
    link_capture_name="IO-to-ECONT-input-link-capture-link-capture-AXI-0"
    bram_name="IO-to-ECONT-input-link-capture-link-capture-AXI-0_FIFO"

    dev.getNode(link_capture_name+".global.link_enable").write(0x1)
    dev.getNode(link_capture_name+".global.explicit_resetb").write(0x0)
    dev.getNode(link_capture_name+".global.explicit_resetb").write(0x1)
    for l in range(12):
        link = "link%i"%l
        dev.getNode(link_capture_name+"."+link+".explicit_resetb").write(0x0)
        dev.getNode(link_capture_name+"."+link+".explicit_resetb").write(0x1)
        dev.getNode(link_capture_name+"."+link+".L1A_offset_or_BX").write(0x0)
        dev.getNode(link_capture_name+"."+link+".capture_mode_in").write(0x1)
        dev.getNode(link_capture_name+"."+link+".aquire_length").write(0x1000)
        
    dev.dispatch()

    for l in range(12):
        link = "link%i"%l
        data = dev.getNode(bram_name+"."+link).readBlock(1000)
        dev.dispatch()
        print([hex(i) for i in data])
        dev.getNode(link_capture_name+"."+link+".aquire").write(0x0)
        dev.getNode(link_capture_name+"."+link+".explicit_rstb_acquire").write(0x0)
        dev.getNode(link_capture_name+"."+link+".explicit_rstb_acquire").write(0x1)
    dev.getNode(link_capture_name+".global.interrupt_enable").write(0x0)
    dev.dispatch()

    # check fast command counters
    reset_roc = dev.getNode("fast-command-fastcontrol-recv-axi-0.counters.link_reset_roct").read()
    dev.dispatch()
    print('reset roct counters %d'%reset_roc)

