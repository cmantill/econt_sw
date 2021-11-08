import os
import uhal
from uhal_config import names,input_nlinks,output_nlinks

import logging
logging.basicConfig()
logger = logging.getLogger('utils')
logger.setLevel(logging.INFO)

# input test vector (input nlinks)
def read_testvector(fname):
    import csv
    data = [[] for l in range(input_nlinks)]

    with open(fname) as f:
        csv_reader = csv.reader(f, delimiter=',')
        for i,row in enumerate(csv_reader):
            if i==0: continue # skip header                                                                                                        
            for l in range(input_nlinks):
                data[l].append(row[l])
    return data

# output test vector (output nlinks)
def save_testvector(fname,data,header=False):
    import csv
    with open( fname, 'w') as f:
        writer = csv.writer(f, delimiter=',')
        if header:
            writer.writerow(['TX_DATA_%i'%l for l in range(len(data[0]))])
        for j in range(len(data)):
            writer.writerow(['{0:08x}'.format(int(data[j][k])) for k in range(len(data[j]))])

# configure IO blocks
def configure_IO(dev,io,io_name='IO'):
    nlinks = input_nlinks if io=='to' else output_nlinks
    delay_mode=0
    if (io_name == "ASIC-IO" and io=="to") or (io_name == "IO" and io=="from"):
        delay_mode = 1

    for l in range(nlinks):
        dev.getNode(names[io_name][io]+".link"+str(l)+".reg0.tristate_IOBUF").write(0x0)
        dev.getNode(names[io_name][io]+".link"+str(l)+".reg0.bypass_IOBUF").write(0x0)
        dev.getNode(names[io_name][io]+".link"+str(l)+".reg0.invert").write(0x0)
        dev.getNode(names[io_name][io]+".link"+str(l)+".reg0.reset_link").write(0x0)
        dev.getNode(names[io_name][io]+".link"+str(l)+".reg0.reset_counters").write(0x1)
        dev.getNode(names[io_name][io]+".link"+str(l)+".reg0.delay_mode").write(delay_mode)
    dev.getNode(names[io_name][io]+".global.global_rstb_links").write(0x1)
    dev.getNode(names[io_name][io]+".global.global_reset_counters").write(0x1)
    import time
    time.sleep(0.001)
    dev.getNode(names[io_name][io]+".global.global_latch_counters").write(0x1)
    dev.dispatch()

# is IO block aligned?
def check_IO(dev,io='from',nlinks=output_nlinks,io_name='IO'):
    IO_delayready = []
    for l in range(nlinks):
        i=0
        delay_ready=0
        while i < 100:
            i+=1
            bit_tr = dev.getNode(names[io_name][io]+".link"+str(l)+".reg3.waiting_for_transitions").read()
            delay_ready = dev.getNode(names[io_name][io]+".link"+str(l)+".reg3.delay_ready").read()
            dev.dispatch()
            logger.debug("%s-IO link%i: bit_tr %d and delay ready %d"%(io,l,bit_tr,delay_ready))
            if delay_ready == 1:
                break
        IO_delayready.append(delay_ready)
    is_aligned = True
    for delay in IO_delayready:
        if delay!=1:
            is_aligned = False
    if is_aligned:
        logging.info("Links %s-IO are aligned"%io)
    else:
        logging.info("Links %s-IO are not aligned"%io)
    return is_aligned
    
# is link capture aligned?
def check_links(dev,lcapture='lc-ASIC',nlinks=output_nlinks):
    import numpy as np
    lc_align = []
    for l in range(nlinks):
        aligned_c = dev.getNode(names[lcapture]['lc']+".link"+str(l)+".link_aligned_count").read()
        error_c = dev.getNode(names[lcapture]['lc']+".link"+str(l)+".link_error_count").read()
        aligned = dev.getNode(names[lcapture]['lc']+".link"+str(l)+".status.link_aligned").read()
        dev.dispatch()
        lc_align.append((aligned_c,error_c,aligned))
    aligned_counter = np.array([int(lc_align[i][0]) for i in range(len(lc_align))])
    error_counter = np.array([int(lc_align[i][1]) for i in range(len(lc_align))])
    is_aligned = np.array([int(lc_align[i][2]) for i in range(len(lc_align))])
    try:
        assert np.all(is_aligned==1)
        assert np.all(aligned_counter==128)
        assert np.all(error_counter==0)
        logger.info('%s: all links are aligned!'%lcapture)
    except AssertionError:
        logger.error('%s: is not aligned:'%lcapture)
        for i in range(len(lc_align)):
            logger.error('LINK-%i: %d %d %d'%(i, is_aligned[i], aligned_counter[i], error_counter[i]))
        return False
    return True

# set link capture to acquire
# mode: 0 (inmediate - writes data to BRAM)
# mode: 1 (writes data starting on a specific BX count)
# mode: 2 (writes data after receiving a fast command)
# mode: 3 (auto-daq mode)
def configure_acquire(dev,lcapture,mode,nwords=4095,nlinks=output_nlinks):
    captures = {'mode_in': 0,
                'L1A': 0,
                'orbitSync': 0,
                'linkreset_ECONt': 0,
                'linkreset_ECONd': 0,
                'linkreset_ROCt': 0,
                'linkreset_ROCd': 0,
            }
    captures[mode] = 1
    if "linkreset" in mode or 'L1A' in mode or 'orbitSync' in mode:
        captures["mode_in"] = 2

    for l in range(nlinks):
        dev.getNode(names[lcapture]['lc']+".link"+str(l)+".L1A_offset_or_BX").write(0)
        dev.getNode(names[lcapture]['lc']+".link"+str(l)+".aquire_length").write(nwords)        
        for key,val in captures.items():
            dev.getNode(names[lcapture]['lc']+".link"+str(l)+".capture_%s"%key).write(val)
    dev.dispatch()

# acquire with fast command
def do_fc_capture(dev,fc,lcapture):
    dev.getNode(names[lcapture]['lc']+".global.aquire").write(0)
    dev.dispatch()
    dev.getNode(names[lcapture]['lc']+".global.aquire").write(1)
    dev.dispatch()
    dev.getNode(names['fc']+".request.%s"%fc).write(0x1);
    dev.dispatch()
    dev.getNode(names[lcapture]['lc']+".global.aquire").write(0)
    dev.dispatch()

# get captured data
def get_captured_data(dev,lcapture,nwords=4095,nlinks=output_nlinks):
    # wait some time until acquisition finishes 
    while True:
        fifo_occupancies = []
        for l in range(nlinks):
            fifo_occupancy = dev.getNode(names[lcapture]['lc']+".link"+str(l)+".fifo_occupancy").read()
            dev.dispatch()
            fifo_occupancies.append(int(fifo_occupancy))
        try:
            assert(fifo_occupancies[0] == nwords)
            for f in fifo_occupancies:
                assert(f == fifo_occupancies[0])
                print(f,fifo_occupancies[0])
            break
        except:
            print('not same fifo occ ',fifo_occupancies)
            continue

    # now look at data
    print('looking at data')
    daq_data = []
    for l in range(nlinks):
        fifo_occupancy = dev.getNode(names[lcapture]['lc']+".link%i"%l+".fifo_occupancy").read()
        dev.dispatch()
        #print(fifo_occupancy)
        if int(fifo_occupancy)>0:
            logger.debug('%s link-capture fifo occupancy link%i %d' %(lcapture,l,fifo_occupancy))
            data = dev.getNode(names[lcapture]['fifo']+".link%i"%l).readBlock(int(fifo_occupancy))
            dev.dispatch()
            daq_data.append([int(d) for d in data])
        else:
            logger.warning('%s link-capture fifo occupancy link%i %d' %(lcapture,l,fifo_occupancy))
    if len(daq_data)>0:
        print(lcapture,len(daq_data[0]))
    try:
        import numpy as np
        transpose = np.array(daq_data).T
        return transpose
    except:
        transpose = [list(x) for x in zip(*daq_data)]
        return transpose
