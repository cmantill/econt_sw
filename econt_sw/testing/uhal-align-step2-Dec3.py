import uhal
from uhal_config import names,input_nlinks,output_nlinks
from uhal_utils import configure_IO,check_IO,configure_acquire,do_fc_capture,get_captured_data,save_testvector,do_capture,check_links
import logging

uhal.disableLogging()

logger = logging.getLogger('debug')
logger.setLevel(logging.DEBUG)

man = uhal.ConnectionManager("file://connection.xml")
dev = man.getDevice("mylittlememory")

# configure fc
dev.getNode(names['fc']+".command.enable_fast_ctrl_stream").write(0x1);
dev.getNode(names['fc']+".command.enable_orbit_sync").write(0x1);
dev.getNode(names['fc']+".command.global_l1a_enable").write(0);
dev.getNode(names['fc']+".bx_link_reset_roct").write(3500)
dev.getNode(names['fc']+".bx_link_reset_rocd").write(3501)
dev.getNode(names['fc']+".bx_link_reset_econt").write(3502)
dev.getNode(names['fc']+".bx_link_reset_econd").write(3503)
dev.dispatch()

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

# check IO blocks are aligned
isIO_aligned = check_IO(dev,io='from',nlinks=output_nlinks)

# check eye width
for link in range(output_nlinks):
    delay_out = dev.getNode(names['IO']['from']+".link%i"%link+".reg3.delay_out").read()
    delay_out_N = dev.getNode(names['IO']['from']+".link%i"%link+".reg3.delay_out_N").read()
    dev.dispatch()
    print(link,int(delay_out),int(delay_out_N))

# configure lc
sync_patterns = {
    'lc-ASIC': 0x122,
    'lc-emulator': 0x122,
    'lc-input': 0xaccccccc,
}
for lcapture in ['lc-input','lc-ASIC','lc-emulator']:
    dev.getNode(names[lcapture]['lc']+".global.link_enable").write(0x1fff)
    dev.getNode(names[lcapture]['lc']+".global.explicit_resetb").write(0x0)
    time.sleep(0.001)
    dev.getNode(names[lcapture]['lc']+".global.explicit_resetb").write(0x1)
    dev.dispatch()
    # set align pattern
    nlinks = input_nlinks if 'input' in lcapture else output_nlinks
    for l in range(nlinks):
        dev.getNode(names[lcapture]['lc']+".link"+str(l)+".align_pattern").write(sync_patterns[lcapture])
        dev.getNode(names[lcapture]['lc']+".link"+str(l)+".fifo_latency").write(0);
        dev.dispatch()

for lcapture in ['lc-ASIC','lc-emulator']:
    # configure link captures to acquire on linkreset-ECONt (4095 words)
    configure_acquire(dev,lcapture,"linkreset_ECONt",nwords=4095,nlinks=output_nlinks)
    
# send link reset econt (once)
lrc = dev.getNode(names['fc-recv']+".counters.link_reset_econt").read();
dev.dispatch()
logger.info('link reset econt counter %i'%lrc)

dev.getNode(names['fc']+".bx_link_reset_econt").write(3550)
dev.dispatch()
dev.getNode(names['fc']+".request.link_reset_econt").write(0x1);
dev.dispatch()
time.sleep(0.1)

lrc = dev.getNode(names['fc-recv']+".counters.link_reset_econt").read();
dev.dispatch()
logger.info('link reset econt counter %i'%lrc)

is_lcASIC_aligned = check_links(dev,lcapture='lc-ASIC',nlinks=output_nlinks)
if not is_lcASIC_aligned:
    # capture data
    raw_input("Need to capture data in output. Press key to continue...")
    do_fc_capture(dev,"link_reset_econt",'lc-ASIC')
    lrc = dev.getNode(names['fc-recv']+".counters.link_reset_econt").read();
    dev.dispatch()
    logger.info('link reset econt counter %i'%lrc)
    data = get_captured_data(dev,'lc-ASIC',nwords=4095,nlinks=output_nlinks)
    save_testvector("lc-ASIC-alignoutput_debug.csv", data)
