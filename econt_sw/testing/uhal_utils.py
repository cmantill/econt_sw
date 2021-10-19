import os
import uhal
import numpy as np
from uhal_config import names,input_nlinks,output_nlinks

import logging
logging.basicConfig()
logger = logging.getLogger('utils')
logger.setLevel(logging.INFO)

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

def save_testvector(fname,data):
    import csv
    with open( fname, 'w') as f:
        writer = csv.writer(f, delimiter=',')
        for j in range(len(data)):
            writer.writerow(['{0:08x}'.format(int(data[j][k])) for k in range(len(data[j]))])

def check_links(dev):
    # is from-IO aligned?
    fromIO_delayready = []
    for l in range(output_nlinks):
        delay_ready = dev.getNode(names['IO']['from']+".link%i"%l+".reg3.delay_ready").read()
        dev.dispatch()
        fromIO_delayready.append(delay_ready)
    try:
        assert np.all( np.array(fromIO_delayready) == 0x01)
        logging.info("All links from-IO are aligned")
    except:
        logging.error("Not all links from-IO are aligned")
        raise
        
    # is ASIC LC aligned?
    lc_align = []
    for l in range(output_nlinks):
        link = "link%i"%l
        aligned_c = dev.getNode(names['lc-ASIC']['lc']+".link%i"%l+".link_aligned_count").read()
        error_c = dev.getNode(names['lc-ASIC']['lc']+".link%i"%l+".link_error_count").read()
        aligned = dev.getNode(names['lc-ASIC']['lc']+".link%i"%l+".status.link_aligned").read()
        dev.dispatch()
        lc_align.append((aligned_c,error_c,aligned))
    aligned_counter = np.array([int(lc_align[i][0]) for i in range(len(lc_align))])
    error_counter = np.array([int(lc_align[i][1]) for i in range(len(lc_align))])
    is_aligned = np.array([int(lc_align[i][2]) for i in range(len(lc_align))])
    try:
        assert np.all(is_aligned==1)
        assert np.all(aligned_counter==128)
        assert np.all(error_counter==0)
        logger.info('ASIC link-capture all links are aligned')
    except AssertionError:
        logger.error('ASIC link-capture is not aligned:')
        for i in range(len(lc_align)):
            logger.error('LINK-%i: %d %d %d'%(i, is_aligned[i], aligned_counter[i], error_counter[i]))
    return True

def get_captured_data(dev,lcapture):
    daq_data = []
    for l in range(output_nlinks):
        fifo_occupancy = dev.getNode(names[lcapture]['lc']+".link%i"%l+".fifo_occupancy").read()
        dev.dispatch()
        if int(fifo_occupancy)>0:
            data = dev.getNode(names[lcapture]['fifo']+".link%i"%l).readBlock(int(fifo_occupancy))
            dev.dispatch()
            daq_data.append([int(d) for d in data])
        else:
            logger.warning('%s link-capture fifo occupancy link%i %d' %(lcapture,l,fifo_occupancy))
    # dev.getNode(names[lcapture]['lc']+".global.interrupt_enable").write(0x0)   
    # dev.dispatch()
    print(lcapture,len(daq_data[0]))
    return np.array(daq_data).T

