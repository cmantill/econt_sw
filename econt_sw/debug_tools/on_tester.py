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

    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")
    uhal.setLogLevelTo(uhal.LogLevel.DEBUG)

    if args.io == "to":
        io_name = "ASIC-IO-IO-to-ECONT-ASIC-IO-blocks-0"
        testvectors_switch_name = "test-vectors-to-ASIC-and-emulator-test-vectors-ipif-switch-mux"
        nlinks = 12
    else:
        io_name = "ASIC-IO-IO-from-ECONT-ASIC-IO-blocks-0"
        nlinks = 13

    for option in args.debug:
        if option=="IO" or option=="IO-invert":
            for l in range(nlinks):
                link = "link%i"%l
                dev.getNode(io_name+"."+link+".reg0.tristate_IOBUF").write(0x0)
                dev.getNode(io_name+"."+link+".reg0.bypass_IOBUF").write(0x0)
                if option=="IO-invert":
                    dev.getNode(io_name+"."+link+".reg0.invert").write(0x1)
                else:
                    dev.getNode(io_name+"."+link+".reg0.invert").write(0x0)
            dev.dispatch()
                    
        if option=="PRBS":
            for l in range(nlinks):
                link = "link%i"%l
                dev.getNode(testvectors_switch_name+"."+link+".output_select").write(0x1)
            dev.dispatch()
