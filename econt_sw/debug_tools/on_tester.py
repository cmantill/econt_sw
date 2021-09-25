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
    #uhal.setLogLevelTo(uhal.LogLevel.DEBUG)
    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")

    if args.io == "to":
        io_name = "ASIC-IO-IO-to-ECONT-ASIC-IO-blocks-0"
        testvectors_switch_name = "test-vectors-to-ASIC-and-emulator-test-vectors-ipif-switch-mux"
        nlinks = 12
    else:
        io_name = "ASIC-IO-IO-from-ECONT-ASIC-IO-blocks-0"
        nlinks = 13

    for option in args.debug:
        if option=="fc":
            dev.getNode("fastcontrol_axi.command.enable_fast_ctrl_stream").write(0x1);
            dev.getNode("fastcontrol_axi.command.enable_orbit_sync").write(0x1);
            
            dev.getNode("fastcontrol_axi.bx_link_reset_roct").write(3500)
            dev.getNode("fastcontrol_axi.bx_link_reset_rocd").write(3501)
            dev.getNode("fastcontrol_axi.bx_link_reset_econt").write(3502)
            dev.getNode("fastcontrol_axi.bx_link_reset_econd").write(3503)
            dev.getNode("fastcontrol_axi.request.link_reset_roct").write(0x1);
            dev.getNode("fastcontrol_axi.request.link_reset_econt").write(0x1);
            dev.dispatch()

        if option=="IO" or option=="IO-invert":
            for l in range(nlinks):
                link = "link%i"%l
                dev.getNode(io_name+"."+link+".reg0.tristate_IOBUF").write(0x0)
                dev.getNode(io_name+"."+link+".reg0.bypass_IOBUF").write(0x0)
                if option=="IO-invert":
                    dev.getNode(io_name+"."+link+".reg0.invert").write(0x1)
                else:
                    dev.getNode(io_name+"."+link+".reg0.invert").write(0x0)

                if args.io=="from":
                    dev.getNode(io_name+"."+link+".reg0.reset_link").write(0x0)
                    dev.getNode(io_name+"."+link+".reg0.reset_counters").write(0x1)
                    dev.getNode(io_name+"."+link+".reg0.delay_mode").write(0x1)

            dev.getNode(io_name+".global.global_rstb_links").write(0x1)
            dev.dispatch()

        if option=="IO-read" and args.io=="from":
            for l in range(nlinks):
                link = "link%i"%l
                bit_tr = dev.getNode(io_name+"."+link+".reg3.waiting_for_transitions").read()
                delay_ready = dev.getNode(io_name+"."+link+".reg3.delay_ready").read()
                dev.dispatch()
                print("link %i: bit_tr %d and delay ready %d"%(link,bit_tr,delay_ready))
                if delay_ready==1:
                    print('DELAY READY!')
                    
        if option=="PRBS":
            for l in range(nlinks):
                link = "link%i"%l
                dev.getNode(testvectors_switch_name+"."+link+".output_select").write(0x1)
            dev.dispatch()
