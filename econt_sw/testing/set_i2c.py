import uhal

if __name__ == "__main__":    
    # define uHal
    uhal.setLogLevelTo(uhal.LogLevel.DEBUG)
    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")
    
    #dev.getNode("ASIC-IO-I2C-I2C-fudge-0.ECONT_ASIC_I2C_address").write(0);
    dev.getNode("ASIC-IO-I2C-I2C-fudge-0.ECONT_emulator_I2C_address").write(1);
