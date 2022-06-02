from PrologixGPIB.TestStand_Controls import psControl
import argparse
from i2c import call_i2c

latency_dict = {
    "RPT": 0,
    "TS": 0,
    "STC": 0,
    "BC": 1,
    "AE": 2,
}

def configure_bypass(idir,base_latency=13):
    # determine algo from directory
    algo = idir.split('_')[0]
    
    # configure output
    from utils.test_vectors import TestVectors
    tv = TestVectors('bypass')
    tv.set_bypass(0)
    tv.configure("",idir,"testOutput.csv")

    # configure input
    tv = TestVectors()
    tv.set_bypass(1)
    tv.configure("",idir,"testInput.csv")
    
    # configure i2c
    call_i2c(args_name='MISC_run',args_value='0')
    yamlFile = f"{idir}/init.yaml"
    logger.info(f"Loading i2c from {yamlFile} for ASIC")
    x = call_i2c(args_yaml=yamlFile, args_i2c="ASIC", args_write=True)    
    call_i2c(args_name='MISC_run',args_value='1')
    
    # set latency
    lc = LinkCapture()
    lc.set_latency(["lc-emulator"],[base_latency+latency_dict[algo]]*14)
    
    # compare output
    num_links = call_i2c(args_name='FMTBUF_eporttx_numen',args_write=False)['ASIC']['RW']['FMTBUF_ALL']['config_eporttx_numen']
    logger.info('Number of links to compare %i'%num_links)
    data = compare_lc(trigger=False,nlinks=num_links,nwords=4095,
                      csv=True,phex=False,odir=idir,fname="sc")

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', dest='dataset', type=str, required=True, help="dataset directory")
    parser.add_argument('--dir', dest='dir', type=str, default=None, help="specify directories to run")
    args = parser.parse_args()    
    
    ps=psControl(host="192.168.0.50")
    v,i=ps.Read_Power("48")

    print(v,i)

    
