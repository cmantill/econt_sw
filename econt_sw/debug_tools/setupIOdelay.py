import uhal

if __name__ == "__main__":

    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")

    dev.getNode("IO-to-ECONT-IO-blocks-0.reg0.delay_mode").write(0x1)
