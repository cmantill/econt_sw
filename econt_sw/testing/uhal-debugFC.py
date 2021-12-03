import uhal
from uhal_config import names

uhal.disableLogging()

man = uhal.ConnectionManager("file://connection.xml")
dev = man.getDevice("mylittlememory")

invert = 1

dev.getNode(names['fc']+".command.enable_fast_ctrl_stream").write(0x1);
dev.getNode(names['fc']+".command.enable_orbit_sync").write(0x1);
#dev.getNode(names['fc']+".command.global_l1a_enable").write(0);

inv = dev.getNode(names['fc']+".command.invert_output").read()
dev.dispatch()
print(inv)
dev.getNode(names['fc']+".command.invert_output").write(invert);
dev.dispatch()
