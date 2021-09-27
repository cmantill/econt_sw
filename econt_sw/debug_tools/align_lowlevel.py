import mmap
import numpy
import time
import os
import logging
from econ_i2c import econ_i2c
import bitstruct
import cython

hexprint = lambda: numpy.printoptions(formatter={'int': lambda x: f'{x:08x}'}, linewidth=120, threshold=10000)

label_to_uio = {}
label_to_size = {}
for uio in os.listdir('/sys/class/uio'):
    try:
        with open(f'/sys/class/uio/{uio}/device/of_node/instance_id') as label_file:
            label = label_file.read().split('\x00')[0]
        with open(f'/sys/class/uio/{uio}/maps/map0/size') as size_file:
            size = int(size_file.read(), 16)

        label_to_uio[label] = uio
        label_to_size[label] = size
        logging.debug(f'UIO device /dev/{uio} has label {label} and is 0x{size:x} bytes')
    except FileNotFoundError:
        pass

def uio_open(label):
    with open(f'/dev/{label_to_uio[label]}', 'r+b') as uio_dev_file:
        return numpy.frombuffer(mmap.mmap(uio_dev_file.fileno(), label_to_size[label], access=mmap.ACCESS_WRITE, offset=0), numpy.uint32)


lc_mem = uio_open("capture-align-compare-ECONT-emulator-link-capture-AXI-Full-IPIF-0")
lc     = uio_open("capture-align-compare-ECONT-emulator-link-capture-link-capture-AXI-0")
LCs = lc.reshape(-1, 16)[1:14]
fc = uio_open("housekeeping-FastControl-fastcontrol-axi-0")
fc_decoder = uio_open("housekeeping-FastControl-fastcontrol-recv-axi-0")
fromIO = uio_open("ASIC-IO-IO-from-ECONT-ASIC-axi-to-ipif-mux-0")[:4*14].reshape(14,4)
toIO = uio_open("ASIC-IO-IO-to-ECONT-ASIC-axi-to-ipif-mux-0")[:4*13].reshape(13,4)
out_switch = uio_open("test-vectors-to-ASIC-and-emulator-test-vectors-ipif-switch-mux")[:8*12].reshape(12,8)
out_stream = uio_open("test-vectors-to-ASIC-and-emulator-test-vectors-ipif-stream-mux")[:4*12].reshape(12,4)
out_brams = [uio_open(f"test-vectors-to-ASIC-and-emulator-test-vectors-out-block{i:02d}-bram-ctrl") for i in range(12)]
i2c = econ_i2c(1)

class IOblocks:
    def __init__(self, backing_mem, Nlinks):
        self.mem = backing_mem
        self.Nlinks = Nlinks
        self.global_fmt = 'p29b1b1b1p32p32p32'
        self.global_names = ['global_counter_latch', 'global_counter_reset', 'global_resetn']
        self.link_fmt = 'p6b1u9u9' + ('b1'*7) + 'u32u32p12b1u9u9b1'
        self.link_names = ['invert', 'delay_offset', 'delay_in', 'counter_latch', 'tristate_IObuf', 'bypass_IObuf',
                           'delay_set', 'delay_mode', 'counter_reset', 'resetn',
                           'bit_counter', 'error_counter',
                           'waiting_for_transition', 'delay_out_N', 'delay_out', 'delay_ready']
        self.names = self.global_names + self.link_names

    def get_global(self):
        return bitstruct.unpack_dict(self.global_fmt, self.global_names, self.mem[0].byteswap())

    def set_global(self, items):
        to_write = {**self.get_global(), **items}
        self.mem[0] = numpy.frombuffer(bitstruct.pack_dict(self.global_fmt, self.global_names, to_write), '>u4')

    def get_link(self, link):
        return bitstruct.unpack_dict(self.link_fmt, self.link_names, self.mem[link+1].byteswap())

    def set_link(self, link, items):
        to_write = {**self.get_link(link), **items}
        self.mem[link+1] = numpy.frombuffer(bitstruct.pack_dict(self.link_fmt, self.link_names, to_write), '>u4')
        
    def get_links(self):
        dt = numpy.dtype([(name, '>u4') for name in self.link_names])
        dicts = [self.get_link(link) for link in range(self.Nlinks)]
        return numpy.array([tuple(d[name] for name in dt.names) for d in dicts], dtype=dt)
            
    def set_links(self, items):
        for k,v in items.items():
            self[k] = v

    def __getitem__(self, key):
        if key in self.global_names:
            return self.get_global()[key]
        elif key in self.link_names:
            return numpy.array([self.get_link(link)[key] for link in range(self.Nlinks)])
        else:
            raise KeyError(key)
            
    def __setitem__(self, key, value):
        if key in self.global_names:
            self.set_global({key: value})
        elif key in self.link_names:
            for link in range(self.Nlinks):
                self.set_link(link, {key: numpy.broadcast_to(value, self.Nlinks)[link]})
        else:
            raise KeyError(key)

fromc = IOblocks(fromIO, 13)
toc = IOblocks(toIO, 12)

toc.set_links({'resetn':0, 'delay_mode': 0, 'invert':0, 'bypass_IObuf': 0, 'tristate_IObuf': 0})
fromc.set_links({'resetn':0, 'delay_mode':1, 'invert':0, 'bypass_IObuf': 0, 'tristate_IObuf': 0})

with numpy.printoptions(formatter={'int': lambda x: f'{x:9d}'}, linewidth=180):
    print('From ECON-T IO:')
    print(f'{"link number"             :25s} {numpy.arange(13)}')
    print(f'{"link resetn"             :25s} {fromc["resetn"]*1}')
    print(f'{"reset counters"          :25s} {fromc["counter_reset"]*1}')
    print(f'{"delay mode"              :25s} {fromc["delay_mode"]*1}')
    print(f'{"delay in"                :25s} {fromc["delay_in"]}')
    print(f'{"delay offset"            :25s} {fromc["delay_offset"]}')
    print(f'{"delay ready"             :25s} {fromc["delay_ready"]*1}')
    print(f'{"delay"                   :25s} {fromc["delay_out"]}')
    print(f'{"eye width"               :25s} {fromc["delay_out_N"]}')
    print(f'{"bits"                    :25s} {fromc["bit_counter"]}')
    print(f'{"bits errors"             :25s} {fromc["error_counter"]}')
    print(f'{"waiting for transitions" :25s} {fromc["waiting_for_transition"]*1}')
    
    print()
    print('To ECON-T IO:')
    print(f'{"link number"             :25s} {numpy.arange(12)}')
    print(f'{"link resetn"             :25s} {toc["resetn"]*1}')
    print(f'{"reset counters"          :25s} {toc["counter_reset"]*1}')
    print(f'{"delay mode"              :25s} {toc["delay_mode"]*1}')
    print(f'{"delay in"                :25s} {toc["delay_in"]}')
    print(f'{"delay offset"            :25s} {toc["delay_offset"]}')
    print(f'{"delay ready"             :25s} {toc["delay_ready"]*1}')
    print(f'{"delay"                   :25s} {toc["delay_out"]}')
    print(f'{"eye width"               :25s} {toc["delay_out_N"]}')
    print(f'{"bits"                    :25s} {toc["bit_counter"]}')
    print(f'{"bits errors"             :25s} {toc["error_counter"]}')
    print(f'{"waiting for transitions" :25s} {toc["waiting_for_transition"]*1}')

with hexprint():
    print(out_switch)

patt_BX1 = 0xaccccccc
patt_BX0 = 0xabcd1234

out_switch[:,0] = 1 # Select the source: 0=BRAM, 1=LFSR
out_switch[:,1] = 256
out_switch[:,2] = patt_BX1
out_switch[:,3] = patt_BX0
out_switch[:,4] = 0xf0000000 # Set the header mask
out_switch[:,5] = 0xa0000000
out_switch[:,6] = 0x90000000

out_stream[:,0] = 1 # Set the BRAM mode
out_stream[:,1] = 1 # Set the BRAM mode

for i in range(12):
    out_brams[i][:] = 0

I2C_addr_emulator = 0x20

# TX sync word
Sync_word = 0b00100100010
i2c.write(I2C_addr_emulator, 0x03a9, Sync_word.to_bytes(2, 'little'))

# Set the maximum bunch counter value to 3563, the number of bunch crossings in one orbit (minus one)
BX_max = 3563
i2c.write(I2C_addr_emulator, 0x0380 + 0x12, BX_max.to_bytes(2, 'little'))

# Set the bunch counter value on an orbit sync fast command to 0 --- but maybe this should not be 0? (JSW)
orbsyn_val = 1 # Needs to be 1 to test STC
i2c.write(I2C_addr_emulator, 0x0380 + 0x14, orbsyn_val.to_bytes(2, 'little'))

# Set the bunch counter value on which to take a snapshot to 4.  This needs to be set so that the
# special BX0 sync pattern from the HGCROC will appear inside the snapshot.
orbsyn_snap = 6
i2c.write(I2C_addr_emulator, 0x0380 + 0x16, orbsyn_snap.to_bytes(2, 'little'))

# Set the match pattern and mask for the word aligner
match_val = (patt_BX0 << 32) | patt_BX1
i2c.write(I2C_addr_emulator, 0x380 + 0x1, match_val.to_bytes(8, 'little'))
match_mask = 0x0000000000000000
i2c.write(I2C_addr_emulator, 0x380 + 0x9, match_mask.to_bytes(8, 'little'))

# Enable snapshot_arm [bit 0], and snapshot_en [bit 1] but do not enable i2c_snapshot_en [bit 2] nor dbg_fc_cnt_clr [bit 3]
i2c.write(I2C_addr_emulator, 0x0380, [0b00000011])

# Turn on automatic alignment for all links
for i in range(12):
    i2c.write(I2C_addr_emulator, 0x0000 + 0x00 + 0x40*i, [0b00000001])

fc[0] = 0x5 # enable FC, enable orbitsync

# Set the BX on which link reset will be sent
fc[3] = (3500 & 0xfff) | ((3501 & 0xfff) << 12) # BX for link reset ROCt, then for link reset ROCd
fc[4] = (3502 & 0xfff) | ((3503 & 0xfff) << 12) # BX for link reset ECONt, then for link reset ECONd
# Send a link reset ROCt fast command
fc[1] |= 0x100000

sel = numpy.copy(numpy.array([i2c.read(I2C_addr_emulator, 0x0014 + 0x01 + 0x40*i, 1)[0] for i in range(12)]))
status = numpy.array([i2c.read(I2C_addr_emulator, 0x0014 + 0x00 + 0x40*i, 1)[0] for i in range(12)])
snapshot = [int.from_bytes(i2c.read(I2C_addr_emulator, 0x0014 + 0x02 + 0x40*i, 24), 'little') for i in range(12)]

print([hex(s) for s in snapshot])

print([hex(snapshot[i] >> sel[i]) for i in range(len(snapshot))])

print(status)

hex((snapshot[0]>> 88) & 0xffffffff)

def try_snap(snap):
    i2c.write(I2C_addr_emulator, 0x0380 + 0x16, snap.to_bytes(2, 'little'))
    i2c.write(I2C_addr_emulator, 0x0380, [0b00000011])
    for i in range(12):
        i2c.write(I2C_addr_emulator, 0x0000 + 0x00 + 0x40*i, [0b00000001])
        
    fc[0] = 0x5 # enable FC, enable orbitsync

    # Set the BX on which link reset will be sent
    fc[3] = (3500 & 0xfff) | ((3501 & 0xfff) << 12) # BX for link reset ROCt, then for link reset ROCd
    fc[4] = (3502 & 0xfff) | ((3503 & 0xfff) << 12) # BX for link reset ECONt, then for link reset ECONd
    # Send a link reset ROCt fast command
    fc[1] |= 0x100000
    
    sel = numpy.copy(numpy.array([i2c.read(I2C_addr_emulator, 0x0014 + 0x01 + 0x40*i, 1)[0] for i in range(12)]))
    status = numpy.array([i2c.read(I2C_addr_emulator, 0x0014 + 0x00 + 0x40*i, 1)[0] for i in range(12)])
    snapshot = [int.from_bytes(i2c.read(I2C_addr_emulator, 0x0014 + 0x02 + 0x40*i, 24), 'little') for i in range(12)]

    return snapshot

for snap in range(20):
    print(snap, hex(try_snap((snap-10)%3564)[0]))

for snap in range(100):
    print(snap, any(['9ccc' in hex(s) for s in try_snap(snap)]))
