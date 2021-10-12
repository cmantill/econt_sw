import uhal
import time
import argparse
import numpy as np
import logging

logging.basicConfig()

"""
Event DAQ using uHAL python2.

Usage:
   python testing/uhal-eventDAQ.py 
"""

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE, NONE",default='NONE')
    
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

    logger = logging.getLogger('align:step:%s'%args.step)
    logger.setLevel(logging.INFO)
    
    names = {
        'IO': {'to': "ASIC-IO-IO-to-ECONT-ASIC-IO-blocks-0",
               'from': "ASIC-IO-IO-from-ECONT-ASIC-IO-blocks-0"},
        'testvectors': {'switch': "test-vectors-to-ASIC-and-emulator-test-vectors-ipif-switch-mux",
                        'stream': "test-vectors-to-ASIC-and-emulator-test-vectors-ipif-stream-mux",
                        'bram': "test-vectors-to-ASIC-and-emulator-test-vectors-out-block00-bram-ctrl"
                    },
        'bypass': {'switch': "econt-emulator-bypass-option-expected-outputs-RAM-ipif-switch-mux",
                   'stream': "econt-emulator-bypass-option-expected-outputs-RAM-ipif-stream-mux"
               },
        'fc': "housekeeping-FastControl-fastcontrol-axi-0",
        'fc-recv': "housekeeping-FastControl-fastcontrol-recv-axi-0",
        'lc-ASIC': {'lc': "capture-align-compare-ECONT-ASIC-link-capture-link-capture-AXI-0",
                    'fifo': "capture-align-compare-ECONT-ASIC-link-capture-link-capture-AXI-0_FIFO",
                    },
        'lc-emulator': {'lc': "capture-align-compare-ECONT-emulator-link-capture-link-capture-AXI-0",
                        'fifo': "capture-align-compare-ECONT-emulator-link-capture-link-capture-AXI-0_FIFO",
                        },
        'stream_compare': "capture-align-compare-compare-outputs-stream-compare-0",

    }
    input_nlinks = 12
    output_nlinks = 13

    # check alignment
    def check_links():
        # is from-IO aligned?
        fromIO_delayready = []
        for l in range(output_nlinks):
            delay_ready = dev.getNode(names['IO']['from']+".link%i"%l+".reg3.delay_ready").read()
            dev.dispatch()
            fromIO_delayready.append(delay_ready)
        try:
            assert np.all( numpy.array(fromIO_delayready) == 0x01)
            logging.info("All links from-IO are aligned")
        except:
            logging.error("Not all links from-IO are aligned")
            raise
        
        # is ASIC link capture aligned
        lc_align = []
        for l in range(output_nlinks):
            link = "link%i"%l
            aligned_c = dev.getNode(names['lc-ASIC']['lc']+".link%i"%l+".link_aligned_count").read()
            error_c = dev.getNode(names['lc-ASIC']['lc']+".link%i"%l+".link_error_count").read()
            aligned = dev.getNode(names['lc-ASIC']['lc']+".link%i"%l+".status.link_aligned").read()
            dev.dispatch()
            lc_align.append((aligned_c,error_c,aligned))
        aligned_counter = np.array([lc_align[i][0] for i in range(len(lc_align))])
        error_counter = np.array([lc_align[i][1] for i in range(len(lc_align))])
        is_aligned = np.array([lc_align[i][2] for i in range(len(lc_align))])
        try:
            assert np.all( aligned_counter==128 and error_counter==0 and is_aligned==0)
                logger.info('ASIC link-capture all links are aligned')
        except:
            logger.error('ASIC link-capture is not aligned:')
            for i in lc_align:
                logger.error('LINK-%i: %d %d %d'%(i, is_aligned, aligned_counter, error_counter))
        return True

    # first, check that links are aligned
    isaligned = check_links()

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
        link = "link%i"%l
        for st in ['switch','stream']:
            for key,value in testvectors_settings[st].items():
                dev.getNode(names['testvectors'][st]+"."+link+"."+key).write(value)
            
        # size of bram is 4096
        out_brams.append([None] * 4096)

        dev.dispatch()

    # set input data
    fname = "/home/HGCAL_dev/src/econt_sw/econt_sw/configs/test_vectors/counterPattern_Oct8/testInput.csv"

    import csv
    data = []
    with open(fname) as f:
        csv_reader = csv.reader(f, delimiter=',')
        for i,row in enumerate(csv_reader):
            if i==0: continue
            for l in range(input_nlinks):
                data[l].append(row[l])

    print(data[:1])


    for l in range(input_nlinks):
        for i,b in enumerate(out_brams[l]):
                if i==0: out_brams[l][i] = 0x90000000
                else:
                    out_brams[l][i] = 0xa0000000
            dev.getNode(names['testvectors']['bram'].replace('00',"%02d"%l)).writeBlock(out_brams[l])
            dev.dispatch()
            time.sleep(0.001)

    # configure bypass to take data from test-vectors
    for l in range(output_nlinks):
        link = "link%i"%l
        dev.getNode(names['bypass']['switch']+"."+link+".output_select").write(0x1)
    dev.dispatch()

    # configure fast commands
    dev.getNode(names['fc']+".command.enable_fast_ctrl_stream").write(0x1);
    dev.getNode(names['fc']+".command.enable_orbit_sync").write(0x1);
        
    # configure link capture (both ASIC and emulator)
    acq_length = 300
    for lcapture in [names['lc-ASIC'],names['lc-emulator']]:
        lcapture = lcapture['lc']
        dev.getNode(lcapture+".global.link_enable").write(0x1fff)
        dev.getNode(lcapture+".global.explicit_resetb").write(0x0)
        time.sleep(0.001)
        dev.getNode(lcapture+".global.explicit_resetb").write(0x1)
        dev.dispatch()
        for l in range(output_nlinks):
            # set lc to capture on L1A
            dev.getNode(lcapture+".link%i"%l+".capture_mode_in").write(0x2)
            dev.getNode(lcapture+".link%i"%l+".capture_L1A").write(0x1)
            dev.getNode(lcapture+".link%i"%l+".capture_linkreset_ECONt").write(0x0)
            dev.getNode(lcapture+".link%i"%l+".capture_linkreset_ROCd").write(0x0)
            dev.getNode(lcapture+".link%i"%l+".capture_linkreset_ROCt").write(0x0)
            dev.getNode(lcapture+".link%i"%l+".capture_linkreset_ECONd").write(0x0)

            dev.getNode(lcapture+".link%i"%l+".L1A_offset_or_BX").write(0)
            
            dev.getNode(lcapture+".link%i"%l+".aquire_length").write(acq_length)
            dev.dispatch()

    # check stream compare
    dev.getNode(names['stream_compare']+".control.reset").write(0x1)
    time.sleep(0.001)
    dev.getNode(names['stream_compare']+".control.latch").write(0x1)
    dev.dispatch()
    word_count = dev.getNode(names['stream_compare']+".word_count").read()
    err_count = dev.getNode(names['stream_compare']+".err_count").read()
    logger.info('Stream compare, word count %d, error count %d'%(word_count,err_count))

    issue_l1a=True
    if issue_l1a:
        # send L1A
        dev.getNode(names['fc']+".command.global_l1a_enable").write(1);
        dev.getNode(names['fc']+".periodic0.enable").write(0);
        dev.getNode(names['fc']+".periodic0.flavor").write(0);
        dev.getNode(names['fc']+".periodic0.enable_follow").write(0);
        dev.getNode(names['fc']+".periodic0.bx",3500);
        dev.getNode(names['fc']+".periodic0.request",1);
        dev.dispatch()
    else:
        # send a L1A with two capture blocks 
        dev.getNode(names['stream_compare']+".trigger").write(0x1)
        dev.dispatch()

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

    # check captured data
    all_data = {}
    for lcapture in [names['lc-ASIC'],names['lc-emulator']]:
        all_data[lcapture] = []
        for l in range(output_nlinks):
            fifo_occupancy = dev.getNode(names['lc-ASIC']['lc']+"."+link+".fifo_occupancy").read()
            dev.dispatch()
            occ = '%d'%fifo_occupancy
            if occ>0:
                data = dev.getNode(names['lc-ASIC']['fifo']+"."+link).readBlock(int(fifo_occupancy))
                dev.dispatch()
                all_data[lcapture].append(data)
            else:
                logger.info('ASIC link-capture fifo occupancy %s %d %i' %(link,fifo_occupancy,len(data)))
        dev.getNode(names['lc-ASIC']['lc']+".global.interrupt_enable").write(0x0)
        dev.dispatch()

    # convert all data to format
