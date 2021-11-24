from econ_i2c import econ_i2c

busId = 1
i2c = econ_i2c(busId) 
i2c_addr = 0x21
print('Testing i2c addr ',i2c_addr)

# to read a register with address addr and size size_byte
readback = i2c.read(i2c_addr, 0x0380, 1)
print('Aligner config ',hex(int.from_bytes(readback, 'little')))

# write
i2c.write(i2c_addr, 0x0380, [0b00000011])
readback = i2c.read(i2c_addr, 0x0380, 1)
print('Aligner write and readback ',hex(int.from_bytes(readback, 'little')))
