#!/usr/bin/env python3

from econ_i2c import econ_i2c

i2c = econ_i2c(1)

# TX sync word
i2c.write(0x20, 0x03a9, [0x22, 0x11])
readback = i2c.read(0x20, 0x03a9, 2)
print("TX Sync word: 0x%02x%02x"%tuple(readback[::-1]))

# Number of output ports enabled (bits 7:4)
i2c.write(0x20, 0x03a9 + 0x7, [0xd0])
readback = i2c.read(0x20, 0x03a9 + 0x7, 1)
print("Read back 0x%02x"%tuple(readback))

# Algorithm select
i2c.write(0x20, 0x0454, [0])
readback = i2c.read(0x20, 0x0454, 1)
print("Algorithm_sel_Density 0x%02x"%tuple(readback))

# Misc (bit 0 = clear errors?; bit 1 = run; others = unused)
i2c.write(0x20, 0x0be9, [0x02])
readback = i2c.read(0x20, 0x0be9, 1)
print("Misc RW 0x%02x"%tuple(readback))

# Output buffer threshold T1
i2c.write(0x20, 0x03a9 + 0x02, [0xff, 0x00])
readback = i2c.read(0x20, 0x03a9 + 0x02, 2)
print("Buffer threshold value T1 0x%02x%02x"%tuple(readback[::-1]))

# Output buffer threshold T2
readback = i2c.read(0x20, 0x03a9 + 0x04, 2)
print("Buffer threshold value T2 0x%02x%02x"%tuple(readback[::-1]))

# Output buffer threshold T3
readback = i2c.read(0x20, 0x03a9 + 0x06, 1)
print("Buffer threshold value T3 0x%02x"%tuple(readback[::-1]))

# Set all of the algorithm thresholds to 2
for i in range(48):
    i2c.write(0x20, 0x0455 + 3*i, [0x02, 0x00, 0x00])

## Set up channel aligner 0
#i2c.write(0x20, 0x0000, [0x0])
#readback = i2c.read(0x20, 0x0000, 1)
#print("CHAL 00 RW config: 0x%02x"%tuple(readback))
#
#readback = i2c.read(0x20, 0x0001, 1)
#print("CHAL 00 RW sel_override_val: 0x%02x"%tuple(readback))
#
## Take a snapshot of one channel's data
#i2c.write(0x20, 0x0380, [0x0])
#readback = i2c.read(0x20, 0x0380, 1)
#print("Aligner config 0x%02x"%tuple(readback))
#
## Check that the snapshot is ready
#readback = i2c.read(0x20, 0x0014, 1)
#print("CHAL 00 RO status: 0x%02x"%tuple(readback))
#
## Read the snapshot
#readback = i2c.read(0x20, 0x0014 + 0x2, 24)
#for i, datum in enumerate(readback):
#    print("Snapshot %2d: 0x%02x"%(i, datum))
#
#readback = i2c.read(0x20, 0x0380, 1)
#print("Aligner config 0x%02x"%tuple(readback))
#
## Check that the snapshot is ready
#readback = i2c.read(0x20, 0x0014, 1)
#print("CHAL 00 RO status: 0x%02x"%tuple(readback))
#
## Test repeated reads
#print("")
#readback = i2c.read(0x20, 0x0000, 1)
#for datum in readback:
#    print("0x%02x"%datum)
#readback = i2c.read(0x20, ndata=1)
#for datum in readback:
#    print("0x%02x"%datum)
#readback = i2c.read(0x20, ndata=2)
#for datum in readback:
#    print("0x%02x"%datum)
#readback = i2c.read(0x20, ndata=2)
#for datum in readback:
#    print("0x%02x"%datum)
#readback = i2c.read(0x20, ndata=2)
#for datum in readback:
#    print("0x%02x"%datum)
#
#print("")
#readback = i2c.read(0x20, 0x0000, 8)
#for datum in readback:
#    print("0x%02x"%datum)
