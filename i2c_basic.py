from econ_i2c import econ_i2c

i2c = econ_i2c(1)

# TX sync word
i2c.write(0x20, 0x03a9, [0x22, 0x11])
