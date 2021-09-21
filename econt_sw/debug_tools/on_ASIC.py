import uhal
import time
import argparse

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('debug', metavar='d', type=str, nargs='+',
                        help='debug options')
    parser.add_argument('--io', type=str, default="to",
                        help='to IO or from IO')
    args = parser.parse_args()

    uhal.disableLogging();
    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")

    if args.io == "to":
        io_name = "IO-to-ECONT-IO-blocks-0"
        link_capture_name="IO-to-ECONT-input-link-capture-link-capture-AXI-0"
        bram_name="IO-to-ECONT-input-link-capture-link-capture-AXI-0_FIFO"
        nlinks = 12
    else:
        io_name = "IO-from-ECONT-IO-blocks-0"
        link_capture_name="IO-from-ECONT-output-link-capture-link-capture-AXI-0"
        bram_name="IO-from-ECONT-output-link-capture-link-capture-AXI-0_FIFO"
        nlinks = 13

    for option in args.debug:

        if option=="fc-read":
            reset_roc = dev.getNode("fast-command-fastcontrol-recv-axi-0.counters.link_reset_roct").read()
            dev.dispatch()
            print('reset roct counters %d'%reset_roc)

        if option=="IO" or option=="IO-invert":
            for l in range(nlinks):
                link = "link%i"%l
                dev.getNode(io_name+"."+link+".reg0.tristate_IOBUF").write(0x0)
                dev.getNode(io_name+"."+link+".reg0.bypass_IOBUF").write(0x0)
                if option=="IO-invert":
                    dev.getNode(io_name+"."+link+".reg0.invert").write(0x1)
                else:
                    dev.getNode(io_name+"."+link+".reg0.invert").write(0x0)

                if args.io=="to":
                    dev.getNode(io_name+"."+link+".reg0.reset_link").write(0x0)
                    dev.getNode(io_name+"."+link+".reg0.reset_counters").write(0x1)
                    dev.getNode(io_name+"."+link+".reg0.delay_mode").write(0x1)

            dev.getNode(io_name+".global.global_rstb_links").write(0x1)
            dev.dispatch()

        if option=="IO-read" and args.io=="to":
            for l in range(nlinks):
                link = "link%i"%l
                #while True:
                bit_tr = dev.getNode(io_name+"."+link+".reg3.waiting_for_transitions").read()
                delay_ready = dev.getNode(io_name+"."+link+".reg3.delay_ready").read()
                dev.dispatch()
                print("%s: bit_tr %d and delay ready %d "%(link,bit_tr,delay_ready))
                if delay_ready==1:
                    print('DELAY READY!')
                    #break;    

        if option=="link-configure" or option=="link-capture":
            dev.getNode(link_capture_name+".global.link_enable").write(0x1fff)
            dev.getNode(link_capture_name+".global.explicit_resetb").write(0x0)
            time.sleep(0.001)
            dev.getNode(link_capture_name+".global.explicit_resetb").write(0x1)
            for l in range(nlinks):
                link = "link%i"%l
                dev.getNode(link_capture_name+"."+link+".L1A_offset_or_BX").write(3500)
                dev.getNode(link_capture_name+"."+link+".capture_mode_in").write(0x1)
                dev.getNode(link_capture_name+"."+link+".aquire_length").write(0x1000)
            dev.dispatch()
            
            if option=="link-align":
                # only needed for from-IO
                 dev.getNode(link_capture_name+".global.link_enable").write(0x1fff)
                 dev.getNode(link_capture_name+".global.explicit_resetb").write(0x0)
                 time.sleep(0.001)
                 dev.getNode(link_capture_name+".global.explicit_resetb").write(0x1)
                 for l in range(nlinks):
                     link = "link%i"%l
                     dev.getNode(link_capture_name+"."+link+".align_pattern").write(0b00100100010)
                     dev.getNode(link_capture_name+"."+link+".L1A_offset_or_BX").write(3500)
                     dev.getNode(link_capture_name+"."+link+".capture_mode_in").write(0x1)
                     dev.getNode(link_capture_name+"."+link+".aquire_length").write(0x1000)
                     dev.getNode(link_capture_name+"."+link+".fifo_latency").write(0x0)
                     dev.dispatch()
            
            if option=="link-capture":
                dev.getNode(link_capture_name+".global.aquire").write(0)
                dev.getNode(link_capture_name+".global.aquire").write(1)
                dev.getNode(link_capture_name+".global.aquire").write(0)
                time.sleep(0.001)
                dev.dispatch()

                for l in range(nlinks):
                    link = "link%i"%l
                    fifo_occupancy = dev.getNode(link_capture_name+"."+link+".fifo_occupancy").read()
                    dev.dispatch()
                    if fifo_occupancy>0:
                        data = dev.getNode(bram_name+"."+link).readBlock(int(fifo_occupancy))
                        dev.dispatch()
                        print('fifo occupancy %s %d %i' %(link,fifo_occupancy,len(data)))
                    #if l==0:
                    #print(link)
                    #print([hex(i) for i in data])
                    dev.getNode(link_capture_name+"."+link+".aquire").write(0x0)
                    dev.getNode(link_capture_name+"."+link+".explicit_rstb_acquire").write(0x0)
                    dev.getNode(link_capture_name+"."+link+".explicit_rstb_acquire").write(0x1)
                    dev.dispatch()
                dev.getNode(link_capture_name+".global.interrupt_enable").write(0x0)
                dev.dispatch()
