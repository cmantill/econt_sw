#!/usr/bin/env python3

#from econ_i2c import econ_i2c
from translator import Translator

#i2c = econ_i2c(1)

# Define pairs from Translator
translator = Translator('ECON-T')
writeCaches = {}
pairs = translator.pairs_from_cfg(translator.paramMap,writeCaches)
writeCaches.update(pairs)

# config from pairs
#translator.cfg_from_pairs(writeCaches)

# read other parammap
paramMap = translator.load_param_map("reg_maps/ECON_I2C_params_test.yaml")['ECON-T']
translator.pairs_from_cfg(paramMap,writeCaches)

# Write and Read
#for addr,val in writeCaches.items():
#    print(addr, val) 
#i2c.write(0x20, addr, val)
#readback = i2c.read(0x20, addr, 1)
#print("0x%02x"%tuple(readback))
