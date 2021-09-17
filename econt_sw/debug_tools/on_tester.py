import uhal
import time

if __name__ == "__main__":

    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")
    uhal.setLogLevelTo(uhal.LogLevel.DEBUG)

    # set invert
    for link in range(12):
        dev.getNode("ASIC-IO-IO-to-ECONT-ASIC-IO-blocks-0.link%i.reg0.invert"%link).write(0x1)
        #dev.getNode("ASIC-IO-IO-to-ECONT-ASIC-IO-blocks-0.link%i.reg0.invert"%link).write(0x0)
    dev.dispatch()

    # check
    for link in range(12):
        bypass = dev.getNode("ASIC-IO-IO-to-ECONT-ASIC-IO-blocks-0.link%i.reg0.bypass_IOBUF"%link).read()
        dev.dispatch()
        print('link %i: bypass %d'%(link,bypass))

    # send PRBS
    for link in range(12):
        dev.getNode("test-vectors-to-ASIC-and-emulator-test-vectors-ipif-switch-mux.link%i.output_select"%link).write(0x1);
    dev.dispatch()
    
    # send econt link reset
    '''
    dev.getNode("fastcontrol_axi.request.link_reset_econt").write(0x1);
    dev.dispatch()
    '''
