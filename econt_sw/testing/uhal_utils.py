import os
import uhal
from uhal_config import names,input_nlinks,output_nlinks

import logging
logging.basicConfig()
logger = logging.getLogger('utils')
logger.setLevel(logging.INFO)

def configure_fc(dev):
    """
    Configure FC
    Do not enable L1A (since this disables link resets)
    """
    dev.getNode(names['fc']+".command.enable_fast_ctrl_stream").write(0x1);
    dev.getNode(names['fc']+".command.enable_orbit_sync").write(0x1);
    dev.getNode(names['fc']+".command.global_l1a_enable").write(0);
    dev.dispatch()

def read_testvector(fname):
    """
    Read input test vector
    TODO: assumes input_nlinks active..
    """
    import csv
    data = [[] for l in range(input_nlinks)]
    with open(fname) as f:
        csv_reader = csv.reader(f, delimiter=',')
        for i,row in enumerate(csv_reader):
            if i==0: continue # skip header                                                                                                        
            for l in range(input_nlinks):
                data[l].append(row[l])
    return data

def save_testvector(fname,data,header=False):
    """
    Save test vector in csv
    TODO: Writes header as TX
    """
    if len(data)>0:
        import csv
        with open( fname, 'w') as f:
            writer = csv.writer(f, delimiter=',')
            if header:
                writer.writerow(['TX_DATA_%i'%l for l in range(len(data[0]))])
            for j in range(len(data)):
                writer.writerow(['{0:08x}'.format(int(data[j][k])) for k in range(len(data[j]))])

def configure_IO(dev,io,io_name='IO',invert=False):
    """
    Configures IO blocks.
    """
    ioblock_settings = {
        "reg0.tristate_IOBUF": 0,
        "reg0.bypass_IOBUF": 0,
        "reg0.invert": 0,
        "reg0.reset_link": 0,
        "reg0.reset_counters": 1,
        "reg0.delay_mode": 0, 
    }
    nlinks = input_nlinks if io=='to' else output_nlinks
    # set delay mode to 1 to those blocks that need to be aligned
    if (io_name == "ASIC-IO" and io=="to") or (io_name == "IO" and io=="from"):
        ioblock_settings["reg0.delay_mode"] = 1
        delay_mode = 1
    # set invert to 1
    if invert:
        ioblock_settings["reg0.invert"] = 1

    # set 
    for l in range(nlinks):
        for key,value in ioblock_settings.items():
            dev.getNode(names[io_name][io]+".link"+str(l)+"."+key).write(value)
        dev.dispatch()

    # reset
    dev.getNode(names[io_name][io]+".global.global_rstb_links").write(0x1)
    dev.getNode(names[io_name][io]+".global.global_reset_counters").write(0x1)
    import time
    time.sleep(1)
    dev.getNode(names[io_name][io]+".global.global_latch_counters").write(0x1)
    dev.dispatch()

def check_IO(dev,io='from',nlinks=output_nlinks,io_name='IO',nit=10000):
    """
    Checks whether IO block is aligned.
    """
    # reset the counters
    dev.getNode(names[io_name][io]+".global.global_reset_counters").write(0x1)
    import time
    time.sleep(1)
    dev.getNode(names[io_name][io]+".global.global_latch_counters").write(0x1)
    dev.dispatch()
    # check the counters
    IO_delayready = []
    for l in range(nlinks):
        i=0
        delay_ready=0
        while i < nit:
            i+=1
            bit_tr = dev.getNode(names[io_name][io]+".link"+str(l)+".reg3.waiting_for_transitions").read()
            delay_ready = dev.getNode(names[io_name][io]+".link"+str(l)+".reg3.delay_ready").read()
            error_counter = dev.getNode(names[io_name][io]+".link"+str(l)+".error_counter").read()
            bit_counter = dev.getNode(names[io_name][io]+".link"+str(l)+".bit_counter").read()
            dev.dispatch()
            logger.info("%s-IO link%i: bit_tr %d, delay ready %d, error counter %i, bit_counter %i"%(io,l,bit_tr,delay_ready,error_counter,bit_counter))
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
    
def check_links(dev,lcapture='lc-ASIC',nlinks=output_nlinks,use_np=True):
    """
    Is link capture aligned?
    Check status registers.
    """
    lc_align = []
    for l in range(nlinks):
        aligned_c = dev.getNode(names[lcapture]['lc']+".link"+str(l)+".link_aligned_count").read()
        error_c = dev.getNode(names[lcapture]['lc']+".link"+str(l)+".link_error_count").read()
        aligned = dev.getNode(names[lcapture]['lc']+".link"+str(l)+".status.link_aligned").read()
        delay_ready = dev.getNode(names[lcapture]['lc']+".link"+str(l)+".status.delay_ready").read()
        waiting_for_trig = dev.getNode(names[lcapture]['lc']+".link"+str(l)+".status.waiting_for_trig").read()
        writing = dev.getNode(names[lcapture]['lc']+".link"+str(l)+".status.writing").read()
        dev.dispatch()
        lc_align.append((aligned_c,error_c,aligned))
        logger.debug('%s link%i aligned: %d delayready: %d waiting: %d writing: %d aligned_c: %d error_c: %d'%(lcapture, l, aligned, delay_ready, waiting_for_trig, writing, aligned_c, error_c))
    aligned_counter = [int(lc_align[i][0]) for i in range(len(lc_align))]
    error_counter = [int(lc_align[i][1]) for i in range(len(lc_align))]
    is_aligned = [int(lc_align[i][2]) for i in range(len(lc_align))]
    if use_np:
        import numpy as np
        is_aligned = np.array(is_aligned)
        aligned_counter = np.array(aligned_counter)
        error_counter = np.array(error_counter)
        try:
            assert np.all(is_aligned==1)
            assert np.all(aligned_counter==128)
            assert np.all(error_counter==0)
            logger.info('%s: all links are aligned!'%lcapture)
        except AssertionError:
            logger.error('%s: is not aligned:'%lcapture)
            for i in range(len(lc_align)):
                bit_err =  dev.getNode(names[lcapture]['lc']+".link"+str(l)+".bit_align_errors").read()
                dev.dispatch()
                logger.error('LINK-%i: is_aligned %d, aligned_counter %d, error_counter %d, bit err %i'%(i, is_aligned[i], aligned_counter[i], error_counter[i],bit_err))
            return False
    else:
        try:
            for l,val in enumerate(aligned_counter):
                assert(is_aligned[l] == 1)
                assert(aligned_counter[l] == 128)
                assert(error_counter[l] == 0)
        except AssertionError:
            logger.error('%s: is not aligned:'%lcapture)
            for i in range(len(lc_align)):
                bit_err =  dev.getNode(names[lcapture]['lc']+".link"+str(l)+".bit_align_errors").read()
                dev.dispatch()
                logger.error('LINK-%i: is_aligned %d, aligned_counter %d, error_counter %d, bit err %i'%(i, is_aligned[i], aligned_counter[i], error_counter[i],bit_err))
        return False
    return True

def configure_acquire(dev,lcapture,mode,nwords=4095,nlinks=output_nlinks,bx=0):
    """
    Set link capture to acquire.
    mode (str): BX,linkreset_ECONt,linkreset_ECONd,linkreset_ROCt,linkreset_ROCd,L1A,orbitSync
    mode: 0 (inmediate - writes data to BRAM) 
    mode: 1 (writes data starting on a specific BX count) 
    mode: 2 (writes data after receiving a fast command)
    mode: 3 (auto-daq mode)
    """
    captures = {
        'mode_in': 0,
        'L1A': 0,
        'orbitSync': 0,
        'linkreset_ECONt': 0,
        'linkreset_ECONd': 0,
        'linkreset_ROCt': 0,
        'linkreset_ROCd': 0,
    }
    if "BX" in mode:
        captures['mode_in'] = 1
    elif "linkreset" in mode or "L1A" in mode or "orbitSync" in mode:
        captures["mode_in"] = 2
    elif "inmediate" in mode:
        captures["mode_in"] = 0
    else:
        logger.warning("Not a valid capture mode!")
        return
    if captures["mode_in"] == 2:
        captures[mode] = 1
    logger.debug("configure acquire with captures ",captures)

    for l in range(nlinks):
        # offset from BRAM write start in 40 MHz clock ticks in L1A capture mode, or BX count to trigger BX capture mode
        dev.getNode(names[lcapture]['lc']+".link"+str(l)+".L1A_offset_or_BX").write(bx) 
        # acquire length
        dev.getNode(names[lcapture]['lc']+".link"+str(l)+".aquire_length").write(nwords)        
        dev.getNode(names[lcapture]['lc']+".link"+str(l)+".total_length").write(nwords)
        for key,val in captures.items():
            dev.getNode(names[lcapture]['lc']+".link"+str(l)+".capture_%s"%key).write(val)
        dev.getNode(names[lcapture]['lc']+".link"+str(l)+".aquire").write(1)
        dev.getNode(names[lcapture]["lc"]+".link"+str(l)+".explicit_rstb_acquire").write(0)
        dev.dispatch()
    dev.getNode(names[lcapture]["lc"]+".global.interrupt_enable").write(0)
    dev.dispatch()

def do_fc_capture(dev,fc,lcapture):
    """
    Acquire data and send a fast command.
    """
    dev.getNode(names[lcapture]['lc']+".global.aquire").write(0)
    dev.dispatch()
    dev.getNode(names[lcapture]['lc']+".global.aquire").write(1)
    dev.dispatch()
    dev.getNode(names['fc']+".request.%s"%fc).write(0x1);
    dev.dispatch()

def do_capture(dev,lcapture,wait=False):
    """
    Acquire
    """
    dev.getNode(names[lcapture]['lc']+".global.aquire").write(0)
    dev.dispatch()
    dev.getNode(names[lcapture]['lc']+".global.aquire").write(1)
    dev.dispatch()
    if wait:
        import time
        time.sleep(0.001)
        raw_input("ready to capture, press link to continue")

def get_captured_data(dev,lcapture,nwords=4095,nlinks=output_nlinks):
    """
    Get captured data
    """
    # wait some time until acquisition finishes 
    while True:
        fifo_occupancies = []
        for l in range(nlinks):
            fifo_occupancy = dev.getNode(names[lcapture]['lc']+".link"+str(l)+".fifo_occupancy").read()
            dev.dispatch()
            fifo_occupancies.append(int(fifo_occupancy))
            if int(fifo_occupancy)==0: 
                logger.warning('no data for %s'%lcapture)
                return []
        try:
            assert(fifo_occupancies[0] == nwords)
            for f in fifo_occupancies:
                assert(f == fifo_occupancies[0])
                logger.debug('fifo occupancies ',fifo_occupancies[0],f)
            break
        except:
            
            print('not same fifo occ ',fifo_occupancies)
            continue

    # now look at data
    daq_data = []
    for l in range(nlinks):
        fifo_occupancy = dev.getNode(names[lcapture]['lc']+".link%i"%l+".fifo_occupancy").read()
        dev.dispatch()
        if int(fifo_occupancy)>0:
            logger.debug('%s link-capture fifo occupancy link%i %d' %(lcapture,l,fifo_occupancy))
            data = dev.getNode(names[lcapture]['fifo']+".link%i"%l).readBlock(int(fifo_occupancy))
            dev.dispatch()
            daq_data.append([int(d) for d in data])
        else:
            logger.warning('%s link-capture fifo occupancy link%i %d' %(lcapture,l,fifo_occupancy))
    if len(daq_data)>0:
        logger.info('Length of captured data for %s: %i',lcapture,len(daq_data[0]))
    try:
        import numpy as np
        transpose = np.array(daq_data).T
        return transpose
    except:
        transpose = [list(x) for x in zip(*daq_data)]
        return transpose

def find_latency(dev,latency,lcapture,bx0=None,savecap=False):
    """
    Find if with that latency we see the BX0 word.
    Uses numpy!
    
    It does captures on link reset econt so capture block needs to set acquire to that.
    If `bx0[l]` is set, then check that that position at which BX0 word is found, is the same as bx0.
    """
    # record the new latency for each elink
    new_latency = {}
    # record the position at which BX0 was found for each elink (this needs to be the same for all elinks) 
    found_BX0 = {}

    # set latency
    for l in range(output_nlinks):
        dev.getNode(names[lcapture]['lc']+".link"+str(l)+".fifo_latency").write(latency[l]);
    dev.dispatch()

    # read latency
    read_latency = {}
    for l in range(output_nlinks):
        lat = dev.getNode(names[lcapture]['lc']+".link"+str(l)+".fifo_latency").read();
        dev.dispatch()
        read_latency[l] = int(lat)
    logger.debug('Written latencies: %s',latency)
    logger.debug('Read latencies: %s',read_latency)

    # capture on link reset econt
    do_fc_capture(dev,"link_reset_econt",lcapture)
    
    # check link reset econt counter 
    lrc = dev.getNode(names['fc-recv']+".counters.link_reset_econt").read()
    dev.dispatch()
    logger.debug('link reset econt counter %i'%lrc)

    # get captured data
    data = get_captured_data(dev,lcapture,nwords=4095,nlinks=output_nlinks)
    #if savecap:
    save_testvector("lc-%s-findlatency-debug.csv"%lcapture, data) 

    # find BX0 in data and in link 0
    BX0_word = 0xf922f922
    BX0_rows,BX0_cols = (data == BX0_word).nonzero()
    logger.info('BX0 sync word found on columns %s',BX0_cols)
    logger.info('BX0 sync word found on rows %s',BX0_rows)
    try:
        assert len(BX0_rows) > 0
        assert (BX0_cols==0).nonzero()
    except AssertionError:
        logger.error('BX0 sync word not found anywhere or in link 0')
        for l in range(output_nlinks):
            new_latency[l] = -1
        return new_latency,found_BX0,data    

    # check that BX0 is found in the same position for all output links
    for l in range(output_nlinks):
        try:
            row_index = (BX0_cols==l).nonzero()[0][0]
            row_link_0 = (BX0_cols==0).nonzero()[0][0]
            assert BX0_rows[row_index] == BX0_rows[row_link_0]
            if bx0:
                assert BX0_rows[row_index] == bx0[row_index]
            logger.info('Latency %i: %s found BX0 word at %d',latency[l],lcapture,BX0_rows[row_index])
            new_latency[l] = latency[l]
            found_BX0[l] = BX0_rows[row_index]
        except AssertionError:
            if bx0:
                logger.warning('BX0 sync word not found for link %i at (pos of link 0): %i or (pos of where bx0 was found for ASIC): %i'%(l,BX0_rows[row_link_0],bx0[row_index]))
            else:
                logger.warning('BX0 sync word not found for link %i at (pos of link 0): %i'%(l,BX0_rows[row_link_0]))
            new_latency[l] = -1

    return new_latency,found_BX0,data


    

    
