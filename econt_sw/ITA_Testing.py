from urllib.request import urlopen
import time
import sys
sys.path.append( 'testing' )
from i2c import call_i2c

URL='https://www-bd.fnal.gov/notifyservlet/www'

useLocal=True
localSCOffset=15

def RO_compare(previousStatus):
    if previousStatus is None: return

    i2c_RO_status=call_i2c(args_name='RO')
    diffs={}
    for chip in i2c_RO_status.keys():
        diffs_chip={}
        for block in i2c_RO_status[chip]['RO'].keys():
            diffs_block={}
            for reg,val in i2c_RO_status[chip]['RO'][block].items():
                if not previousStatus[chip]['RO'][block][reg]==val:
                    diffs_block[reg]=(previousStatus[chip]['RO'][block][reg],val)
            if not diffs_block=={}:
                diffs_chip[block]=diffs_block
        if not diffs_chip=={}:
            diffs[chip] = diffs_chip
    if diffs=={}:
        print('RO MATCH')
    else:
        import pprint
        pprint.pprint(diffs)

prevROstatus=None
try:
    while True:
        if useLocal:
            _time=round((time.time()-localSCOffset)%60,1)
        else:
            response = urlopen(URL).read()
            _time = float(str(response).split('SC time</a> = ')[1].split(' / ')[0])
        
        print(_time)
        if (_time < 5):
            print(_time, 'PULSE IS COMING')
        elif _time>20 and _time<25:
            print(_time, 'CHECK I2C STATUS')
            call_i2c(args_compare=True)
            RO_compare(prevROstatus)
        elif _time>40 and _time<45:
            print(_time, 'WRITE I2C')
            call_i2c(args_yaml='zmq_i2c/reg_maps/ECON_I2C_params_regmap.yaml',args_write=True)
            prevROstatus=i2c_RO_status=call_i2c(args_name='RO')
        time.sleep(5)

except KeyboardInterrupt:
    print('\nClosing.')

