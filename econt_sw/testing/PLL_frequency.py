import mmap
import numpy
import os
import logging
import bitstruct

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

clk = uio_open('FC-FC-clk-generator')

FPFDmin = 10
FPFDmax = 450
FVCOmin = 800
FVCOmax = 1600

Ms = numpy.arange(2, 128.1, 0.125)
Os = numpy.concatenate([[1], numpy.arange(2, 128.1, 0.125)])
Ds = numpy.arange(1, 106.0001)

fIN = 100

fs = {}
for D in Ds:
    fFB = fIN / D
    if fFB >= FPFDmin and fFB <= FPFDmax:
        for M in Ms:
            fVCO = fFB * M
            if fVCO >= FVCOmin and fVCO <= FVCOmax:
                for O in Os:
                    fOUT = fVCO / O
                    if fOUT not in fs:
                        fs[fOUT] = (D, M, O)

allfs = numpy.sort(numpy.array(list(fs.keys())))

f = 320
k = numpy.searchsorted(allfs, f)
D, M, O = fs[allfs[k]]
print(allfs[k], k, D, M, O, fIN/D, fIN*M/D, fIN*M/(D*O))

clk[0x80] = int.from_bytes(bitstruct.pack('u6u10u8u8', 1, int((M%1)*1000), int(M), int(D)), 'big')
clk[0x82] = int.from_bytes(bitstruct.pack('u14u10u8', 1, int((O%1)*1000), int(O)), 'big')
clk[0x97] = 3