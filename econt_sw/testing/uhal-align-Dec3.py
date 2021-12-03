import uhal
from uhal_config import names,input_nlinks,output_nlinks
from uhal_utils import configure_IO,check_IO,configure_acquire,do_fc_capture,get_captured_data,save_testvector,do_capture
import logging

uhal.disableLogging()

logger = logging.getLogger('debug')
logger.setLevel(logging.DEBUG)

man = uhal.ConnectionManager("file://connection.xml")
dev = man.getDevice("mylittlememory")

# configure IO
for io in names['IO'].keys():
    nlinks = input_nlinks if io=='to' else output_nlinks
    delay_mode = 1 if io=='from' else 0
    for l in range(nlinks):
        dev.getNode(names['IO'][io]+".link"+str(l)+".reg0.tristate_IOBUF").write(0x0)
        dev.getNode(names['IO'][io]+".link"+str(l)+".reg0.bypass_IOBUF").write(0x0)
        dev.getNode(names['IO'][io]+".link"+str(l)+".reg0.reset_link").write(0x0)
        dev.getNode(names['IO'][io]+".link"+str(l)+".reg0.reset_counters").write(0x1)
        dev.getNode(names['IO'][io]+".link"+str(l)+".reg0.delay_mode").write(delay_mode)
        dev.getNode(names['IO'][io]+".link"+str(l)+".reg0.invert").write(0x1)
    dev.getNode(names['IO'][io]+".global.global_rstb_links").write(0x1)
    dev.getNode(names['IO'][io]+".global.global_reset_counters").write(0x1)
    import time
    time.sleep(0.001)
    dev.getNode(names['IO'][io]+".global.global_latch_counters").write(0x1)
    dev.dispatch()

# configure fc
dev.getNode(names['fc']+".command.enable_fast_ctrl_stream").write(0x1);
dev.getNode(names['fc']+".command.enable_orbit_sync").write(0x1);
dev.getNode(names['fc']+".command.global_l1a_enable").write(0);
dev.getNode(names['fc']+".bx_link_reset_roct").write(3500)
dev.getNode(names['fc']+".bx_link_reset_rocd").write(3501)
dev.getNode(names['fc']+".bx_link_reset_econt").write(3502)
dev.getNode(names['fc']+".bx_link_reset_econd").write(3503)
dev.dispatch()

# set clock (40MHz)
select = 0
dev.getNode("housekeeping-AXI-mux-0.select").write(select);
dev.dispatch()

# check IO blocks are aligned
#isIO_aligned = check_IO(dev,io='from',nlinks=output_nlinks)

# setup normal output in test-vectors
out_brams = []
testvectors_settings = {
    "output_select": 0x0,
    "n_idle_words": 255,
    "idle_word": 0xaccccccc,
    "idle_word_BX0": 0x9ccccccc,
    "header_mask": 0x00000000,
    "header": 0xa0000000,
    "header_BX0": 0x90000000,
}

for l in range(input_nlinks):
    for key,value in testvectors_settings.items():
        dev.getNode(names['testvectors']['switch']+".link"+str(l)+"."+key).write(value)            
    # size of bram is 4096
    out_brams.append([None] * 4095)
    dev.dispatch()

# set zero-data with headers
for l in range(input_nlinks):
    for i,b in enumerate(out_brams[l]):
        if i==0: 
            out_brams[l][i] = 0x90000000
        else:
            out_brams[l][i] = 0xa0000000
    dev.getNode(names['testvectors']['bram'].replace('00',"%02d"%l)).writeBlock(out_brams[l])
    dev.dispatch()
    time.sleep(0.001)

# configure link captures                                                                                                                                                                                                             
sync_patterns = {'lc-ASIC': 0x122,
                 'lc-emulator': 0x122,
                 'lc-input': 0xaccccccc,
}
for lcapture in ['lc-ASIC']:
    dev.getNode(names[lcapture]['lc']+".global.link_enable").write(0x1fff)
    dev.getNode(names[lcapture]['lc']+".global.explicit_resetb").write(0x0)
    time.sleep(0.001)
    dev.getNode(names[lcapture]['lc']+".global.explicit_resetb").write(0x1)
    dev.dispatch()
    nlinks = input_nlinks if 'input' in lcapture else output_nlinks
    for l in range(nlinks):
        dev.getNode(names[lcapture]['lc']+".link"+str(l)+".align_pattern").write(sync_patterns[lcapture])
        dev.getNode(names[lcapture]['lc']+".link"+str(l)+".fifo_latency").write(0);
        dev.dispatch()
        
# config
#for lcapture in ['lc-ASIC']:
#    configure_acquire(dev,lcapture,"linkreset_ROCt",nwords=4095,nlinks=output_nlinks)
    
lrc = dev.getNode(names['fc-recv']+".counters.link_reset_roct").read();
dev.dispatch()
logger.info('link reset roct counter %i'%lrc)

dev.getNode(names['fc']+".request.link_reset_roct").write(0x1);
dev.dispatch()
time.sleep(0.001)

lrc = dev.getNode(names['fc-recv']+".counters.link_reset_roct").read();
dev.dispatch()
logger.info('link reset roct counter %i'%lrc)
