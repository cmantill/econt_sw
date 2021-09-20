import uhal

if __name__ == "__main__":    
    # define uHal
    uhal.setLogLevelTo(uhal.LogLevel.DEBUG)
    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")
    
    # set i2c address of ASIC (default 0 = 0x20)
    dev.getNode("ASIC-IO-I2C-I2C-fudge-0.ECONT_ASIC_I2C_address").write(0);

    # set i2c address of Emulator (default 1 = 0x20)
    dev.getNode("ASIC-IO-I2C-I2C-fudge-0.ECONT_emulator_I2C_address").write(1);
