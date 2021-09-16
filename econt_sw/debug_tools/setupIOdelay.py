import uhal

if __name__ == "__main__":

    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")

    for link in range(0,11):
        dev.getNode("IO-to-ECONT-IO-blocks-0.link%i.reg0.delay_mode"%link).write(0x1)
