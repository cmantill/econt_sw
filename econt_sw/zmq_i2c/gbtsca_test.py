import iic

myiic=iic.iic(mode="I2C")
i2caddr = 0x20 # asume that address is 0x20
myiic.connect(addr=i2caddr)

# use myiic to read back a register address
reg = 0x0380 # this one has size byte 1 - what do you do with register address with more that 1 bytes?
ID = "1" # not sure which ID this corresponds to
readback = myiic.read_lpgbt_trig(ID, reg)

# to map the register names to addresses you can use translator class
from translator import Translator
translator = Translator('ECON-T')

# Read all default registers into a default dict
default = translator.pairs_from_cfg()

# Load test map and expand config
paramMap = translator.load_param_map("../configs/init-align_emulator.py")['ECON-T']
pairs = translator.pairs_from_cfg(paramMap)

# Read previous values of addresses in test map
writeCaches = {}
for addr,vals in pairs.items():
    size_byte = vals[1]
    # again here I am not sure what ID should be
    # also what happens if the register's size byte is > 1?
    readback = myiic.read_lpgbt_trig(ID, addr)
