import uhal
from uhal_config import names,input_nlinks,output_nlinks
from uhal_utils import configure_IO

uhal.disableLogging()

man = uhal.ConnectionManager("file://connection.xml")
dev = man.getDevice("mylittlememory")

# configure IO blocks
for io in names['IO'].keys():
    configure_IO(dev,io,io_name='IO')
    nlinks = input_nlinks if io=='to' else output_nlinks
    for l in range(nlinks):
        dev.getNode(names['IO'][io]+".link"+str(l)+".reg0.invert").write(0x1)
    dev.dispatch()

# send PRBS in elink outputs
testvectors_settings = {
    "output_select": 0x1, #PRBS mode
    "n_idle_words": 256,
    "idle_word": 0xaccccccc,
    "idle_word_BX0": 0x9ccccccc,
    "header_mask": 0xf0000000, # impose headers                                                                                                                                                     
    "header": 0xa0000000,
    "header_BX0": 0x90000000,
}
for l in range(input_nlinks):
    for key,value in testvectors_settings.items():
        dev.getNode(names['testvectors']['switch']+".link"+str(l)+"."+key).write(value)
    dev.getNode(names['testvectors']['stream']+".link"+str(l)+".sync_mode").write(0x1)
    dev.getNode(names['testvectors']['stream']+".link"+str(l)+".ram_range").write(0x1)
    dev.getNode(names['testvectors']['stream']+".link"+str(l)+".force_sync").write(0x0)
dev.dispatch()

# configure fc
dev.getNode(names['fc']+".command.enable_fast_ctrl_stream").write(0x1);
dev.getNode(names['fc']+".command.enable_orbit_sync").write(0x1);
dev.getNode(names['fc']+".command.global_l1a_enable").write(0);

