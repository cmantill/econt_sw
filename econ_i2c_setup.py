#!/usr/bin/env python3

from econ_i2c import econ_i2c

i2c = econ_i2c(1)

# TX sync word, same as used in ECONT simulation [https://github.com/dnoonan08/ECONT_Emulator]
Sync_word = 0b00100100010 # 11 bits
i2c.write(0x20, 0x03a9, [Sync_word & 0xff, (Sync_word >> 8) & 0xff])
readback = i2c.read(0x20, 0x03a9, 2)
print("TX Sync word: 0x%02x%02x"%tuple(readback[::-1]))

# Number of output ports enabled (bits 7:4)
# From ECONT simulation [https://github.com/dnoonan08/ECONT_Emulator]
TX_en = 13
Use_sum = 0
STC_type = 0
i2c.write(0x20, 0x03a9 + 0x7, [((TX_en & 0xf) << 4) | ((Use_sum & 0x1) << 2) | (STC_type & 0x3)])
readback = i2c.read(0x20, 0x03a9 + 0x7, 1)
print("Read back 0x%02x"%tuple(readback))

# Algorithm select
algo = 0 # 0: threshold sum
density = 1 # 1: high density
i2c.write(0x20, 0x0454, [((density & 0x1) << 3) | (algo & 0x7)])
readback = i2c.read(0x20, 0x0454, 1)
print("Algorithm_sel_Density 0x%02x"%tuple(readback))

## Misc (bit 0 = clear errors?; bit 1 = run; others = unused)
#i2c.write(0x20, 0x0be9, [0x02])
#readback = i2c.read(0x20, 0x0be9, 1)
#print("Misc RW 0x%02x"%tuple(readback))

# Output buffer threshold T1
Buff_T1 = 312 # From ECONT simulation [https://github.com/dnoonan08/ECONT_Emulator]
i2c.write(0x20, 0x03a9 + 0x02, [Buff_T1 & 0xff, (Buff_T1 >> 8) & 0xff])

# Output buffer threshold T2
Buff_T2 = 288 # From ECONT simulation [https://github.com/dnoonan08/ECONT_Emulator]
i2c.write(0x20, 0x03a9 + 0x02, [Buff_T2 & 0xff, (Buff_T2 >> 8) & 0xff])

# Output buffer threshold T3
Buff_T3 = 25 + 26 # From ECONT simulation [https://github.com/dnoonan08/ECONT_Emulator]
i2c.write(0x20, 0x03a9 + 0x02, [Buff_T3])

# Drop LSB
Drop_LSB = 3 # From ECONT simulation [https://github.com/dnoonan08/ECONT_Emulator]
i2c.write(0x20, 0x04e5, [Drop_LSB])

# Got the thresholds used in the software ECONT simulation [https://github.com/dnoonan08/ECONT_Emulator]
thresholds = [47, 47, 47, 47, 47, 47, 47, 47,
              47, 47, 47, 47, 47, 47, 47, 47,
	      47, 47, 47, 47, 47, 47, 47, 47,
              47, 47, 47, 47, 47, 47, 47, 47,
              47, 47, 47, 47, 47, 47, 47, 47,
              47, 47, 47, 47, 47, 47, 47, 47]
for i in range(48):
    i2c.write(0x20, 0x0455 + 3*i, [thresholds[i] & 0xff, (thresholds[i] >> 8) & 0xff, (thresholds[i] >> 16) & 0xff])

# Got the calibration values used in the software ECONT simulation [https://github.com/dnoonan08/ECONT_Emulator]
calvalues = [348, 347, 335, 336, 347, 348, 335, 335,
             323, 323, 311, 311, 325, 324, 312, 314,
             307, 293, 304, 318, 280, 267, 279, 291,
             303, 290, 302, 315, 329, 316, 328, 340,
             263, 276, 274, 261, 289, 302, 300, 287,
             286, 299, 298, 286, 261, 274, 274, 262]
for i in range(48):
    i2c.write(0x20, 0x03f4 + 2*i, [calvalues[i] & 0xff, (calvalues[i] >> 8) & 0xff])

# Got the MUX selections used in the software ECONT simulation [https://github.com/dnoonan08/ECONT_Emulator]
mux_selects = [ 7,  4,  5,  6,  3,  1,  0,  2,
                8,  9, 10, 11, 14, 13, 12, 15,
               23, 20, 21, 22, 19, 17, 16, 18,
               25, 24, 26, 27, 30, 31, 28, 29,
               38, 37, 39, 46, 36, 34, 33, 35,
               40, 32, 41, 42, 47, 45, 43, 44]
for i in range(48):
    i2c.write(0x20, 0x03c4 + i, [mux_selects[i]])

# Set the maximum bunch counter value to 3563, the number of bunch crossings in one orbit (minus one)
i2c.write(0x20, 0x0380 + 0x12, [3563 & 0xff, (3563 >> 8) & 0xff])

# Set the bunch counter value on an orbit sync fast command to 0 --- but maybe this should not be 0? (JSW)
orbsyn_val = 10
i2c.write(0x20, 0x0380 + 0x14, [orbsyn_val & 0xff, (orbsyn_val >> 8) & 0xff])

# Set the bunch counter value on which to take a snapshot to 0 --- not entirely sure how this works yet (JSW)
i2c.write(0x20, 0x0380 + 0x16, [0, 0])

# Set the match pattern and mask for the word aligner
match_val = 0x9cccccccaccccccc
i2c.write(0x20, 0x380 + 0x1, [(match_val >> 8*i) & 0xff for i in range(8)])
match_mask = 0x0000000000000000
i2c.write(0x20, 0x380 + 0x9, [(match_mask >> 8*i) & 0xff for i in range(8)])
