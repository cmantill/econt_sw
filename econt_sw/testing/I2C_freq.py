#!/usr/bin/env python3

import mmap
import numpy
import time
import os

byteprint = lambda: numpy.printoptions(formatter={'int': lambda x: f'{x:02x}'}, linewidth=120, threshold=10000)

class i2c_lowlevel:
    def __init__(self, uio_name='axi-iic-0'):
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
            except FileNotFoundError:
                pass

        with open(f'/dev/{label_to_uio[label]}', 'r+b') as uio_dev_file:
            self.i2cm = numpy.frombuffer(mmap.mmap(uio_dev_file.fileno(), label_to_size[label], access=mmap.ACCESS_WRITE, offset=0), numpy.uint32)
    
    def reg(addr, doc):
        def getter(self):
            return self.i2cm[addr//4]
        def setter(self, value):
            self.i2cm[addr//4] = value
        return property(getter, setter, doc=doc)
        
    GIE = reg(0x01C, "General Interrupt Enable (GIE)")
    ISR = reg(0x020, "Interrupt Status Register (ISR)")
    IER = reg(0x028, "Interrupt Enable Register (IER)")
    SOFTR = reg(0x040, "Soft Reset (SOFTR)")
    CR = reg(0x100, "Control Register (CR)")
    SR = reg(0x104, "Status Register (SR)")
    TX_FIFO = reg(0x108, "Transmit FIFO (TX_FIFO)")
    RX_FIFO = reg(0x10C, "Receive FIFO (RX_FIFO)")
    ADR = reg(0x110, "Target Address (ADR)")
    TX_FIFO_OCY = reg(0x114, "Transmit FIFO Occupancy (TX_FIFO_OCY)")
    RX_FIFO_OCY = reg(0x118, "Receive FIFO Occupancy (RX_FIFO_OCY)")
    TEN_ADR = reg(0x11C, "Target ten-bit address (TEN_ADR)")
    RX_FIFO_PIRQ = reg(0x120, "Receive FIFO Programmable Depth Interrupt Register (RX_FIFO_PIRQ)")
    GPO = reg(0x124, "General Purpose Output (GPO)")
    TSUSTA = reg(0x128, "Timing: Setup for Start (TSUSTA)")
    TSUSTO = reg(0x12C, "Timing: Setup for Stop (TSUSTO)")
    THDSTA = reg(0x130, "Timing: Hold for Start (THDSTA)")
    TSUDAT = reg(0x134, "Timing: Setup for Data (TSUDAT)")
    TBUF = reg(0x138, "Timing: Bus Free Time (TBUF)")
    THIGH = reg(0x13C, "Timing: High time (THIGH)")
    TLOW = reg(0x140, "Timing: Low time (TLOW)")
    THDDAT = reg(0x144, "Timing: Hold for Data (THDDAT)")
    
    def set_timing(self, AXI_clk_freq_in_MHz, SCL_freq_in_kHz):
        F = SCL_freq_in_kHz
        AXIf = AXI_clk_freq_in_MHz
        timing_regs = { 100: (5700, 5000, 4300, 550, 5000),
                        400: ( 900,  900,  900, 400, 1600),
                       1000: ( 380,  380,  380, 170,  620)}
        susta, susto, hdsta, sudat, buf = timing_regs[F]
        self.TSUSTA = susta * AXIf // 1000
        self.TSUSTO = susto * AXIf // 1000
        self.THDSTA = hdsta * AXIf // 1000
        self.TSUDAT = sudat * AXIf // 1000
        self.TBUF   = buf   * AXIf // 1000
        self.THIGH  = int(numpy.ceil(AXIf*1000000 / (2 * F * 1000))) - 7
        self.TLOW   = int(numpy.ceil(AXIf*1000000 / (2 * F * 1000))) - 8
        self.THDDAT = 1
        
    def write(self, address, data):
        assert len(data) < 15
        self.CR = 0

        self.TX_FIFO = (address << 1) | (1 << 8)
        for datum in data[:-1]:
            self.TX_FIFO = datum
        self.TX_FIFO = data[-1] | (1 << 9)

        self.CR = 0x9
        time.sleep(0.01)
        self.CR = 0
        
    def read(self, address, Nwords):
        assert Nwords < 15
        self.CR = 0
        self.RX_FIFO_PIRQ = 0x0F

        self.TX_FIFO = (address << 1) | 1 | (1 << 8)
        self.TX_FIFO = Nwords | (1 << 9)

        self.CR = 0x9
        time.sleep(0.01)
        self.CR = 0
        
        return numpy.array([numpy.copy(self.RX_FIFO) for i in range(Nwords)])
    
    def checkstatus(self):
        assert self.RX_FIFO_OCY == 0
        assert self.TX_FIFO_OCY == 0
        assert self.SR == 0xC0

I = i2c_lowlevel()
I.SOFTR = 0xA
I.checkstatus()

I.set_timing(AXI_clk_freq_in_MHz=160, SCL_freq_in_kHz=1000)
I.checkstatus()

I.write(address=0x20, data=[0x55, 0xab, 0x7f])
I.checkstatus()

with byteprint():
    print(I.read(address=0x20, Nwords=14))

I.checkstatus()
