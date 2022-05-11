from hexactrl_interface import hexactrl_interface
hexactrl=hexactrl_interface()
hexactrl.empty_fifo()
hexactrl.configure(True,511,4095,nlinks=13)

x_=''

while x_!='q':
    hexactrl.start_daq()

    x_=input()
    err,data=hexactrl.stop_daq(frow=36,capture=(x_!=''))
    if (x_!='') and int(err)>0:
        print('ASIC')
        for x in data[:8]:
            print(','.join(list(x)))
        print('emulator')
        for x in data[8:16]:
            print(','.join(list(x)))
        diff=data[:8]==data[8:16]
        for x in diff:
            print(','.join([str(y) for y in x]))

