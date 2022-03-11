from hexactrl_interface import hexactrl_interface
hexactrl=hexactrl_interface()

hexactrl.configure(True,511,4095)

hexactrl.start_daq()

input()
data=hexactrl.stop_daq()
