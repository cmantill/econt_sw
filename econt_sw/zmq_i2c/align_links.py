#!/usr/bin/env python3

import argparse
import logging
import time
import mmap
import numpy
import os
from econ_i2c import econ_i2c

parser = argparse.ArgumentParser(description="Set up ECON-T emulator system and align all links")
group = parser.add_mutually_exclusive_group()
group.add_argument('--log', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], metavar='LEVEL', help='logging level {DEBUG, INFO, WARNING, ERROR, CRITICAL}')
group.add_argument('-q', action='store_true', help='quiet (set logging level to ERROR)')
group.add_argument('-v', action='store_true', help='verbose (set logging level to DEBUG)')
args = parser.parse_args()

if args.v:
    loglevel = logging.DEBUG
elif args.q:
    loglevel = logging.ERROR
else:
    loglevel = getattr(logging, args.log.upper())

logging.basicConfig(level=loglevel, format='%(levelname)s:%(asctime)s: %(message)s')

logging.info("Finding relevant device files")

label_to_uio = {}
label_to_size = {}
for uio in os.listdir('/sys/class/uio'):
    try:
        with open(f'/sys/class/uio/{uio}/device/of_node/label') as label_file:
            label = label_file.read().split('\x00')[0]
        with open(f'/sys/class/uio/{uio}/maps/map0/size') as size_file:
            size = int(size_file.read(), 16)
            
        label_to_uio[label] = uio
        label_to_size[label] = size
        logging.debug(f'UIO device /dev/{uio} has label {label} and is 0x{size:x} bytes')
    except FileNotFoundError:
        pass

print(label_to_uio)
print(label_to_size)
def uio_open(label):
    with open(f'/dev/{label_to_uio[label]}', 'r+b') as uio_dev_file:
        return numpy.frombuffer(mmap.mmap(uio_dev_file.fileno(), label_to_size[label], access=mmap.ACCESS_WRITE, offset=0), numpy.uint32)

logging.info("Open all of the relevant device files")
lc_mem = uio_open("link-capture-AXI-Full-IPIF-0")
lc = uio_open("link-capture-link-capture-AXI-0")
LCs = lc.reshape(-1, 16)[1:14]
fc = uio_open("FastControl-fastcontrol-axi-0")
fromIO = uio_open("from-ECONT-IO-axi-to-ipif-mux-0")[:4*14].reshape(14,4)
toIO = uio_open("to-ECONT-IO-axi-to-ipif-mux-0")[:4*13].reshape(13,4)
out_switch = uio_open("eLink-outputs-0-ipif-switch-mux")
out_stream = uio_open("eLink-outputs-0-ipif-stream-mux")
out_brams = [uio_open(f"eLink-outputs-0-out-block{i:02d}-bram-ctrl") for i in range(12)]
i2c = econ_i2c(1)

print(out_stream)

logging.info("Setting up the eLink output to send the link reset pattern and stream one complete orbit from RAM")
patt_BX1 = 0xaccccccc
patt_BX0 = 0x9ccccccc
for i in range(12):
    out_switch[4*i] = 0 # Select the stream from RAM as the source
    out_switch[4*i + 1] = 255 # Send 255 words in the link reset pattern
    out_switch[4*i + 2] = patt_BX1 # Send this word for almost all of the link reset pattern
    out_switch[4*i + 3] = patt_BX0 # Send this word on BX0 during the link reset pattern

for i in range(12):
    out_stream[4*i] = 1 # Stream one complete orbit from RAM before looping
    out_stream[4*i + 1] = 1

#with open('EPORTRX_data.csv', 'r') as datafile:
#    for lineno, line in enumerate(datafile):
#        if lineno >= 1:
#            for port_number, datum in enumerate(line.split('\n')[0].split(',')[1:]):
#                value = int(datum)
#                assert (value & 0xf0000000) == 0
#                out_brams[port_number][lineno-1] = value

logging.info("Setting up the output RAMs")
# Fill all 12 RAMs with zeros except for the headers
for i in range(12):
    out_brams[i][1:] = 0xa0000000 # Almost all words get this header
    out_brams[i][0] = 0x90000000 # Special header for BX0

logging.info("Setting up the ECON-T")
# TX sync word
Sync_word = 0b00100100010
i2c.write(0x20, 0x03a9, Sync_word.to_bytes(2, 'little'))

# Algorithm select
algo = 3 # 0: threshold sum, 1: Super Trigger Cell, 2: Best Choice (disabled), 3: repeater, 4: Autoencoder (Disabled)
density = 1 # 1: high density
i2c.write(0x20, 0x0454, [((density & 0x1) << 3) | (algo & 0x7)])

# Number of output ports enabled (bits 7:4)
TX_en = 13
Use_sum = 0
STC_type = 0
i2c.write(0x20, 0x03a9 + 0x7, [((TX_en & 0xf) << 4) | ((Use_sum & 0x1) << 2) | (STC_type & 0x3)])

# Output buffer threshold T1
Buff_T1 = 52 # This must be at least 52 for the econ-t emulator to work
i2c.write(0x20, 0x03a9 + 0x02, Buff_T1.to_bytes(2, 'little'))

# Set the maximum bunch counter value to 3563, the number of bunch crossings in one orbit (minus one)
BX_max = 3563
i2c.write(0x20, 0x0380 + 0x12, BX_max.to_bytes(2, 'little'))

# Set the bunch counter value on an orbit sync fast command to 0 --- but maybe this should not be 0? (JSW)
orbsyn_val = 1 # Needs to be 1 to test STC
i2c.write(0x20, 0x0380 + 0x14, orbsyn_val.to_bytes(2, 'little'))

# Set the bunch counter value on which to take a snapshot to 4.  This needs to be set so that the
# special BX0 sync pattern from the HGCROC will appear inside the snapshot.
orbsyn_snap = 4
i2c.write(0x20, 0x0380 + 0x16, orbsyn_snap.to_bytes(2, 'little'))

# Set the match pattern and mask for the word aligner
match_val = (patt_BX0 << 32) | patt_BX1
i2c.write(0x20, 0x380 + 0x1, match_val.to_bytes(8, 'little'))
match_mask = 0x0000000000000000
i2c.write(0x20, 0x380 + 0x9, match_mask.to_bytes(8, 'little'))

# Enable snapshot_arm [bit 0], and snapshot_en [bit 1] but do not enable i2c_snapshot_en [bit 2] nor dbg_fc_cnt_clr [bit 3]
i2c.write(0x20, 0x0380, [0b00000011])

# Turn on automatic alignment for all links
for i in range(12):
    i2c.write(0x20, 0x0000 + 0x00 + 0x40*i, [0b00000001])

logging.info("Switching on IO")
# Reset elinks and then switch on IO
toIO[1:,0]   = 0b110; toIO[1:,0]   = 0b101
fromIO[1:,0] = 0b110; fromIO[1:,0] = 0b101

logging.info("Sending 3 link resets to get IO delays set up properly")
for i in range(3):
    fc[0] = (1 << 0) | (1 << 2) | (1 << 18)
    time.sleep(0.001) # Sleep for long enough to be sure the link reset was actually sent
    fc[0] = (1 << 0) | (1 << 2)

logging.info("Setting up link capture")
# Enable all 13 links
lc[2] = 0x1fff
# Reset all links
lc[7] = 0
time.sleep(0.001)
lc[7] = 1
# Set the alignment pattern of all 13 links to 0x01220122
LCs[:,1] = Sync_word #| (Sync_word << 16)
# Set the capture mode of all 13 links to 2 (L1A)
LCs[:,2] = 2
# Set the BX offset of all 13 links
LCs[:,3] = (LCs[:,3] & 0xffff0000) | 10
# Set the acquire length of all 13 links
N_acquire = 256
LCs[:,5] = N_acquire
# Set the latency buffer based on the IO delays
delay_out = (fromIO[1:,3] >> 1) & 0x1ff
LCs[:,3] = (LCs[:,3] & 0xffff) | ((1*(delay_out < 0x100)) << 16)
# Tell link capture block to do an acquisition
LCs[:,4] = 1

logging.info("Sending a link reset and L1A together, to capture the reset sequence")
# Set the BX on which link reset will be sent
fc[12] = 3550  # Sync pattern from eLink_outputs appears in the snapshot 2 BX later?
fc[4] = 3549 # BX on which L1A will be sent
# Send a link reset fast command and an L1A
fc[0] = (1 << 0) | (1 << 2) | (1 << 18) | (1 << 20)
time.sleep(0.001) # Sleep for long enough to be certain we actually send them
# Clear the link reset and L1A request bits
fc[0] = (1 << 0) | (1 << 2)

sel = numpy.array([i2c.read(0x20, 0x0014 + 0x01 + 0x40*i, 1)[0] for i in range(12)])
status = numpy.array([i2c.read(0x20, 0x0014 + 0x00 + 0x40*i, 1)[0] for i in range(12)])
snapshot = [int.from_bytes(i2c.read(0x20, 0x0014 + 0x02 + 0x40*i, 24), 'little') for i in range(12)]
with numpy.printoptions(formatter={'int':lambda x: f'{x:08x}'}, linewidth=120):
    for i in range(12):
        logging.debug(f'Chan Aligner {i:02d} sel 0x{sel[i]:02x}, status 0x{status[i]:02x}, snapshot 0x{snapshot[i]:048x}')

try:
    assert numpy.all(status == 0x03)
    logging.info('All ECON-T channels aligned')
except AssertionError:
    logging.error(f'Failed to align ECON-T channels {(status != 0x03).nonzero()[0]}')
    raise

logging.info("Check link capture alignment status")
LC_alignment = LCs[:,8]
logging.debug(f"Links aligned {LC_alignment}")
try:
    assert numpy.all((LC_alignment & 0x1) == 0x1)
    logging.info("All links are word-aligned")
except AssertionError: 
    for i in range(LCs.shape[0]):
        if (LC_alignment[i] & 0x1) != 0x1:
            logging.warning(f'Link capture channel {i+1} is not aligned')

logging.info("Reading out captured data")
FIFO_occupancy = numpy.copy(lc.reshape(-1, 16)[1:14][:,0xe])
with numpy.printoptions(linewidth=120):
    logging.debug(f'Number of words acquired on each channel: {FIFO_occupancy}')

try:
    assert numpy.all(FIFO_occupancy == N_acquire)
except AssertionError:
    logging.error(f'Failed to acquire {N_acquire} words')
    raise

outdata = numpy.array([[numpy.copy(lc_mem[j]) for i in range(FIFO_occupancy[j])] for j in range(13)]).T

BX0_Sync_16 = (0xf800 | Sync_word)
BX0_Sync_32 = (BX0_Sync_16 << 16) | BX0_Sync_16

BX0_rows, BX0_cols = (outdata == BX0_Sync_32).nonzero()
logging.debug(f'BX0 sync word found on rows    {BX0_rows}')
logging.debug(f'BX0 sync word found on columns {BX0_cols}')

try:
    assert len(BX0_rows) > 0
except AssertionError:
    logging.error('BX0 sync word not found anywhere')
    with numpy.printoptions(formatter={'int':lambda x: f'{x:08x}'}, linewidth=120):
        logging.debug(f'Captured data: {outdata[:30]}')
    raise


try:
    assert numpy.all(BX0_rows == BX0_rows[0])
    assert numpy.all(BX0_cols == numpy.arange(13))
    logging.info('All link capture channels are fully aligned')
except AssertionError:
    logging.error('Relative alignment of links failed; check latency buffer settings')
    with numpy.printoptions(formatter={'int':lambda x: f'{x:08x}'}, linewidth=120):
        logging.debug(f'Captured data snippet: {outdata[BX0_rows[0]]}')
    raise
