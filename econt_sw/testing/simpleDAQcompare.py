from hexactrl_interface import hexactrl_interface
hexactrl=hexactrl_interface()
hexactrl.empty_fifo()
hexactrl.configure(True,511,4095,nlinks=13)

hexactrl.start_daq()

input()
err,data=hexactrl.stop_daq(frow=36)
if int(err)>0:
    print('ASIC')
    for x in data[:8]:
        print(','.join(list(x)))
    print('emulator')
    for x in data[8:16]:
        print(','.join(list(x)))
    diff=data[:8]==data[8:16]
    for x in diff:
        print(','.join([str(y) for y in x]))
hexactrl.start_daq()

input()
err,data2=hexactrl.stop_daq(frow=36)
if int(err)>0:
    print('ASIC')
    for x in data2[:8]:
        print(','.join(list(x)))
    print('emulator')
    for x in data2[8:16]:
        print(','.join(list(x)))
    diff=data2[:8]==data2[8:16]
    for x in diff:
        print(','.join([str(y) for y in x]))
