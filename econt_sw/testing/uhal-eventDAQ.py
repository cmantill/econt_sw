import uhal
import time
import argparse
import numpy as np
import logging
logging.basicConfig()

from uhal_config import names,input_nlinks,output_nlinks

from uhal_utils import check_links,read_testvector,get_captured_data,save_testvector

"""
Event DAQ using uHAL python2.

Usage:
   python testing/uhal-eventDAQ.py --idir INPUTDIR
"""

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE, NONE",default='NONE')
    parser.add_argument("--capture", dest="capture", action="store",
                        help="capture data with one of the options", choices=["l1a","compare","bx"], required=True)
    parser.add_argument('--idir',dest="idir",type=str, required=True, help='test vector directory')    
    args = parser.parse_args()

    if args.logLevel.find("ERROR")==0:
        uhal.setLogLevelTo(uhal.LogLevel.ERROR)
    elif args.logLevel.find("WARNING")==0:
        uhal.setLogLevelTo(uhal.LogLevel.WARNING)
    elif args.logLevel.find("NOTICE")==0:
        uhal.setLogLevelTo(uhal.LogLevel.NOTICE)
    elif args.logLevel.find("DEBUG")==0:
        uhal.setLogLevelTo(uhal.LogLevel.DEBUG)
    elif args.logLevel.find("INFO")==0:
        uhal.setLogLevelTo(uhal.LogLevel.INFO)
    else:
        uhal.disableLogging()

    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")

    logger = logging.getLogger('eventDAQ')
    logger.setLevel(logging.INFO)

    # first, check that links are aligned
    isaligned = check_links(dev)

    # read latency values from aligned link captures
    latency_values = {}
    for lcapture in ['lc-ASIC','lc-emulator']:
        latency_values[lcapture] = []
        for l in range(output_nlinks):
            latency = dev.getNode(names[lcapture]['lc']+".link"+str(l)+".fifo_latency").read();
            dev.dispatch()
            latency_values[lcapture].append(int(latency))
    print('FIFO latency: ',latency_values)
            
    # setup test-vectors
    out_brams = []
    testvectors_settings = {
        "switch": {"output_select": 0x0,
                   "n_idle_words": 255,
                   "idle_word": 0xaccccccc,
                   "idle_word_BX0": 0x9ccccccc,
                   "header_mask": 0x00000000, # do not set headers
                   "header": 0xa0000000,
                   "header_BX0": 0x90000000,
                   },
        "stream": {"sync_mode": 0x1,
                   "ram_range": 0x1,
                   "force_sync": 0x0,
                   }
    }
    for l in range(input_nlinks):
        for st in ['switch','stream']:
            for key,value in testvectors_settings[st].items():
                dev.getNode(names['testvectors'][st]+".link"+str(l)+"."+key).write(value)
            
        # size of bram is 4096
        out_brams.append([None] * 4096)
        
        dev.dispatch()

    # set input data
    fname = args.idir+"/testInput.csv"
    data = read_testvector(fname)
    for l in range(input_nlinks):
        for i,b in enumerate(out_brams[l]):
            out_brams[l][i] = int(data[l][i%3564],16)
        dev.getNode(names['testvectors']['bram'].replace('00',"%02d"%l)).writeBlock(out_brams[l])
    dev.dispatch()
    time.sleep(0.001)

    # configure bypass to take data from test-vectors
    for l in range(output_nlinks):
        dev.getNode(names['bypass']['switch']+".link"+str(l)+".output_select").write(0x1)
    dev.dispatch()

    # configure fast commands
    dev.getNode(names['fc']+".command.enable_fast_ctrl_stream").write(0x1);
    dev.getNode(names['fc']+".command.enable_orbit_sync").write(0x1);

    # configure link capture (both ASIC and emulator)
    acq_length = 300
    for lcapture in ['lc-ASIC','lc-emulator']:
        for l in range(output_nlinks):
            # TODO: add bx option
            # set lc to capture on L1A
            dev.getNode(names[lcapture]['lc']+".link%i"%l+".capture_mode_in").write(0x2)
            dev.getNode(names[lcapture]['lc']+".link%i"%l+".capture_L1A").write(0x1)
            dev.getNode(names[lcapture]['lc']+".link%i"%l+".capture_linkreset_ECONt").write(0x0)
            dev.getNode(names[lcapture]['lc']+".link%i"%l+".capture_linkreset_ROCd").write(0x0)
            dev.getNode(names[lcapture]['lc']+".link%i"%l+".capture_linkreset_ROCt").write(0x0)
            dev.getNode(names[lcapture]['lc']+".link%i"%l+".capture_linkreset_ECONd").write(0x0)

            dev.getNode(names[lcapture]['lc']+".link%i"%l+".L1A_offset_or_BX").write(0)
            
            dev.getNode(names[lcapture]['lc']+".link%i"%l+".aquire_length").write(acq_length)
            dev.dispatch()
            
            # set latency?
            dev.getNode(names[lcapture]['lc']+".link"+str(l)+".fifo_latency").write(latency_values[lcapture][l])
            dev.dispatch()
            lat = dev.getNode(names[lcapture]['lc']+".link"+str(l)+".fifo_latency").read()
            dev.dispatch()
            print(lcapture,l,int(lat))

    # check stream compare
    dev.getNode(names['stream_compare']+".control.reset").write(0x1)
    time.sleep(0.001)
    dev.getNode(names['stream_compare']+".control.latch").write(0x1)
    dev.dispatch()
    word_count = dev.getNode(names['stream_compare']+".word_count").read()
    err_count = dev.getNode(names['stream_compare']+".err_count").read()
    dev.dispatch()
    logger.info('Stream compare, word count %d, error count %d'%(word_count,err_count))

    if args.capture == "l1a":
        print('capture l1a')
        # send L1A
        dev.getNode(names['fc']+".command.global_l1a_enable").write(1);
        dev.getNode(names['fc']+".periodic0.enable").write(0); # to get a L1A once - not every orbit
        dev.getNode(names['fc']+".periodic0.flavor").write(0); # 0 to get a L1A
        dev.getNode(names['fc']+".periodic0.enable_follow").write(0); # does not depend on other generator
        dev.getNode(names['fc']+".periodic0.bx").write(3500);
        dev.getNode(names['fc']+".periodic0.request").write(1);
        dev.dispatch()
    elif args.capture == "compare":
        # send a L1A with two capture blocks 
        dev.getNode(names['stream_compare']+".trigger").write(0x1)
        dev.dispatch()
    else:
        logger.error("No capture mode provided")

    # tell link capture to do an acquisition
    dev.getNode(names['lc-ASIC']['lc']+".global.aquire").write(0)
    dev.getNode(names['lc-emulator']['lc']+".global.aquire").write(0)
    dev.dispatch()
    dev.getNode(names['lc-ASIC']['lc']+".global.aquire").write(1)
    dev.getNode(names['lc-emulator']['lc']+".global.aquire").write(1)
    dev.dispatch()
    dev.getNode(names['lc-ASIC']['lc']+".global.aquire").write(0)
    dev.getNode(names['lc-emulator']['lc']+".global.aquire").write(0)
    dev.dispatch()

    time.sleep(0.1)

    # wait some time until acquisition has finished
    for lcapture in ['lc-ASIC','lc-emulator']:
        while True:
            fifo_occupancies = []
            for l in range(output_nlinks):
                fifo_occupancy = dev.getNode(names[lcapture]['lc']+".link"+str(l)+".fifo_occupancy").read()
                dev.dispatch()
                fifo_occupancies.append(int(fifo_occupancy))
            try:
                assert( fifo_occupancies[0] == 300)
                assert(np.all(np.array(fifo_occupancies) == fifo_occupancies[0]))
                break
            except:
                print('fifo occ ',fifo_occupancies)
                continue

    # check captured data
    all_data = {}
    for lcapture in ['lc-ASIC','lc-emulator']:
        all_data[lcapture] = get_captured_data(dev,lcapture)
        
    # convert all data to format
    for key,data in all_data.items():
        save_testvector( args.idir+"/%s-Output_header.csv"%key, data, header=True)

    # reset fc
    dev.getNode(names['fc']+".command.global_l1a_enable").write(0);
