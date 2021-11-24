from econ_i2c import econ_i2c

busId = 1
i2c = econ_i2c(busId) 
i2c_addr = 0x20 

# to read a register with address addr and size size_byte
addr = 0x0300 # for example, CH_ERR_0INPUT_ALL registers
size_byte = 1
i2c.read(i2c_addr, addr, size_byte)
