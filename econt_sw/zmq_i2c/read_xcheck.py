from econ_i2c import econ_i2c
import argparse

parser = argparse.ArgumentParser(description='Read and write')
parser.add_argument('--name', type=str, default=None, help='Write name from dictionary')
parser.add_argument('--value', type=str, default=None, help="Value to write")
args = parser.parse_args()

busId = 1
i2c = econ_i2c(busId) 
i2c_addr = 0x20
print('Testing i2c addr ',hex(i2c_addr))

# read back
addr_map = {
    "run": [0x0bec, 1, 0x01],
    
    "fc_locked": [0x03a6, 2, 0x01],
    "fc_inverted": [0x03a6, 0, 0x01],
    "fc_error": [0x03a5, 4, 0x01],
    "fc_invert": [0x03a5, 3, 0x01],
    "fc_edge_sel": [0x03a5, 0, 0x01],
    
    "PLL_output_clk_sel": [0x0517+0x19, 12, 0x07, 2],
    "PLL_ref_clk_sel": [0x0517+0x19, 15, 0x01, 2],
    "PLL_VCObypass": [0x0517+0x0d, 24, 0x01, 5],
    "PLL_lfEnable": [0x0517+0x12, 24, 0x01, 4],

    "PLL__enableCapBankOverride": [0x0188c888+0x12, 27, 0x01, 4],
    
    "PLL_not_locked_timeout": [0x0533+0x03, 3, 0x01, 2],
    "PLL_lfstate": [0x0533, 0, 0x03, 3],
    "PLL_lflocked": [0x0533, 3, 0x01, 3],
    "PLL_lfInstLock": [0x0533, 2, 0x01, 3],
    "PLL_lflosscount": [0x0533, 4, 0xff, 3],
    "PLL_smstate": [0x0533, 14, 0x0f, 3],
    "PLL_smlocked": [0x0533, 18, 0x01, 3],
    
    "PUSM_state": [0x0bed, 0, 0x0f],

    "ERX0_enable": [0x04e6, 0, 0x01],
}

names = addr_map.keys()
if args.name:
    names =args.name.split(',')
values = []
if args.value:
    values = args.value.split(',') 
    values = [int(v) for v in values]
     
for i,key in enumerate(names):
    try:
        val = addr_map[key]
    except:
        print(f"{key} not in dict")
        continue

    size_byte = 1
    if len(val)>3: size_byte = val[3]

    print(f'Reading {key}')
    size_byte = val[3] if len(val)>3 else 1
    reg_value = i2c.read(i2c_addr, val[0], size_byte)
    if isinstance(reg_value,list):
        reg_value = int.from_bytes(reg_value, 'little')
    else:
        reg_value = reg_value
    print('read reg value ',reg_value,hex(reg_value))
    if len(val)>1:
        value = (reg_value >> val[1]) & val[2]
    else:
        value = reg_value
    print(key,hex(value))

