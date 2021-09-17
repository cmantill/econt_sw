import uhal
import time

if __name__ == "__main__":

    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")
    uhal.setLogLevelTo(uhal.LogLevel.DEBUG)

    # send PRBS
    for link in range(12):
        dev.getNode("test-vectors-to-ASIC-and-emulator-test-vectors-ipif-switch-mux.link%i.output_select"%link).write(0x1);
    dev.dispatch()

    # for i in range(10):
    #     dev.getNode("fastcontrol_axi.request.link_reset_econt").write(0x1);
    #     dev.dispatch()
    #     time.sleep(0.001)
