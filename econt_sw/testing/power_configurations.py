import argparse
import glob
import os

from PrologixGPIB.TestStand_Controls import psControl
from i2c import call_i2c
from utils.link_capture import LinkCapture
from utils.test_vectors import TestVectors
from utils.stream_compare import StreamCompare
from eTx import compare_lc

latency_dict = {
    "RPT": 0,
    "TS": 0,
    "STC": 0,
    "BC": 1,
    "AE": 2,
}

def configure_bypass(idir,algo,base_latency=13):
    """
    # configure output
    tv = TestVectors('bypass')
    tv.set_bypass(0)
    tv.configure("",idir,"testOutput.csv")
    """
    # configure i2c
    call_i2c(args_name='MISC_run',args_value='0')
    yamlFile = f"{idir}/init.yaml"
    x = call_i2c(args_yaml=yamlFile, args_i2c="ASIC", args_write=True)    
    call_i2c(args_name='MISC_run',args_value='1')
    
    """
    # set latency
    lc = LinkCapture()
    lc.set_latency(["lc-emulator"],[base_latency+latency_dict[algo]]*13)
    
    # compare output
    num_links = call_i2c(args_name='FMTBUF_eporttx_numen',args_write=False)['ASIC']['RW']['FMTBUF_ALL']['config_eporttx_numen']
    print('Number of links to compare ',num_links)
    data = compare_lc(True,num_links,nwords=4095)

    if data is not None:
        for lcapture,data_lc in data.items():
            for i,row in enumerate(tv.fixed_hex(data_lc,6)[:40]):
                print(f'{lcapture} {i}: '+",".join(map(str,list(row))))
                print('.'*50)
    """

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', dest='dataset', type=str, required=True, help="dataset directory")
    parser.add_argument('--dirs', dest='dirs', type=str, default=None, help="specify directories to run")
    parser.add_argument('--latency', dest='latency', type=int, default=13, help="latency to emulator with bypass")
    args = parser.parse_args()    
    
    ps=psControl(host="192.168.0.50")
    p,v,i = ps.Read_Power(48)
    print(f'Power: {"On" if int(p) else "Off"}, Voltage: {float(v):.4f} V, Current: {float(i):.4f} A')

    power = {}
    thresholds = list(range(0,1000,10))
    thresholds.append(1000)
    thresholds.append(5000)
    thresholds.append(10000)
    thresholds.append(50000)
    thresholds.append(100000)
    thresholds.append(500000)
    thresholds.append(1000000)
    thresholds.append(4194303)
    for threshold in thresholds:
        call_i2c(args_name='ALGO_threshold_val_[0-47]',args_value='%i'%threshold)
        p,v,i = ps.Read_Power(48)
        print(threshold,v,i)
        power[threshold] = float(i)*float(v)

    import pickle
    with open('varythreshold_netx2.pkl','wb') as f:
        pickle.dump(power,f)

    for key,val in power.items():
        print(key,f'{float(val):.4f}')

    """
    set_input = False
    for idir in glob.glob(f"{args.dataset}/*/testOutput.csv"):
        dirname = os.path.dirname(idir)
        basedir = os.path.basename(dirname)
        algo = basedir.split('_')[0]
        if args.dirs is not None:
            if basedir not in args.dirs.split(','):
                continue

        if not set_input:
	    # configure input
            tv = TestVectors()
            tv.set_bypass(1)
            tv.configure("",dirname,"../testInput.csv")
            set_input = True
        
        # configure_bypass(dirname,algo,args.latency)
        print(idir)
        print('48 ',ps.Read_Power(48))
        print('50 ',ps.Read_Power(48))
    """
    
