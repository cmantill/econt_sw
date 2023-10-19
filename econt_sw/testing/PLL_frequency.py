import mmap
import numpy as np
import os
import logging
import bitstruct
from i2c import I2C_Client
from time import sleep
import uhal
from PLL_class import pll_freq_setup
import argparse
import json
import sys
import time

start = time.time()
fname = "none"
if("--fname" in  sys.argv):
    fname= sys.argv[sys.argv.index("--fname") + 1]

i2cClient = I2C_Client()
pllObj = pll_freq_setup()
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
        return np.frombuffer(mmap.mmap(uio_dev_file.fileno(), label_to_size[label], access=mmap.ACCESS_WRITE, offset=0), np.uint32)

clk = uio_open('FC-FC-clk-generator')

##
xml_path = "/opt/cms-hgcal-firmware/hgc-test-systems/active/uHAL_xml"
connections_file = f"file://{xml_path}/connections.xml"
man = uhal.ConnectionManager(connections_file)
dev = man.getDevice("TOP")
##
allowedCapSelectVals=np.array([  0,   1,   2,   3,   4,   5,   6,   7,   8,   9,  10,  11,  12,
                                 13,  14,  15,  24,  25,  26,  27,  28,  29,  30,  31,  56,  57,
                                 58,  59,  60,  61,  62,  63, 120, 121, 122, 123, 124, 125, 126,
                                 127, 248, 249, 250, 251, 252, 253, 254, 255, 504, 505, 506, 507,
                                 508, 509, 510, 511])
##
frequencies = np.arange(35, 44, (1/8))
frequencies = frequencies*8
b = []
frequency_locked = []
i2cClient.call(args_yaml="../configs/startup.yaml",args_i2c='ASIC',args_write=True)
for i in range(len(frequencies)):
    f_actual, D, M, O, fVCO = pllObj.freq_info(frequencies[i])
    print(f_actual, D, M, O, fVCO)
    ##
    dev.getNode("clk_wiz.divclk_divide").write(int(D))
    dev.getNode("clk_wiz.clkFBout_mult").write(int(M))
    dev.getNode("clk_wiz.clkFBout_frac").write(int((M%1)*1000))
    dev.getNode("clk_wiz.clkout0_divide").write(int(O))
    dev.getNode("clk_wiz.clkout0_frac").write(int((O%1)*1000))
    dev.dispatch()
    dev.getNode("clk_wiz.default").write(1)
    dev.getNode("clk_wiz.load").write(1)
    dev.dispatch()
    ### end of added code ###
    ## hard reset from i2c fudge
    dev.getNode("I2C-I2C-fudge-0.resets.ECONT_ASIC_SOFT_RESETB").write(0)
    dev.dispatch()
    dev.getNode("I2C-I2C-fudge-0.resets.ECONT_ASIC_SOFT_RESETB").write(1)
    dev.dispatch()
    ##
    sleep(0.01)
    ##future code to change the cap select setting
    a = []
    for j in allowedCapSelectVals:
        i2cClient.call('PLL_*CapSelect',args_value=str(j))
        sleep(0.05)
        status = i2cClient.call(args_name='PLL_lfLocked')
        pll_locked = status['ASIC']['RO']['PLL_ALL']['pll_read_bytes_2to0_lfLocked']
        a.append(pll_locked)
        #if pll_locked == 1:
        #    frequency_locked.append(frequencies[i])
    ##
    print(a)
    b.append(a)
#min_freq = frequency_locked[0]
#max_freq = frequency_locked[-1]
#freq_dict = {"min_freq": min_freq, "max_freq": max_freq}
with open(f'/home/HGCAL_dev/acampbell/econt_sw/econt_sw/testing/plldata/{fname}.csv','w') as filehandle:
        json.dump(b, filehandle)
elapsed = time.time() - start
print(elapsed)
