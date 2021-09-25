import uhal
import time
import argparse

"""
To be run on ASIC.
"""

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    uhal.disableLogging();
    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")

    io_name_to = "IO-to-ECONT-IO-blocks-0"
    input_link_capture_name="IO-to-ECONT-input-link-capture-link-capture-AXI-0"
    input_bram_name="IO-to-ECONT-input-link-capture-link-capture-AXI-0_FIFO"
    input_nlinks = 12

    # configure link capture
    dev.getNode(input_link_capture_name+".global.link_enable").write(0x1fff)
    dev.getNode(input_link_capture_name+".global.explicit_resetb").write(0x0)
    time.sleep(0.001)
    dev.getNode(input_link_capture_name+".global.explicit_resetb").write(0x1)
    dev.dispatch()
    
    # configure links to capture on ECONt
    for l in range(input_nlinks):
        link = "link%i"%l
        dev.getNode(input_link_capture_name+"."+link+".align_pattern").write(0b00100100010)
        dev.getNode(input_link_capture_name+"."+link+".L1A_offset_or_BX").write(3500)
        dev.getNode(input_link_capture_name+"."+link+".capture_mode_in").write(0x1)
        #dev.getNode(input_link_capture_name+"."+link+".capture_linkreset_ECONt").write(0x1)                             
        #dev.getNode(input_link_capture_name+"."+link+".capture_mode_in").write(0x2)                                     
        #dev.getNode(input_link_capture_name+"."+link+".capture_L1A").write(0)                                           
        #dev.getNode(input_link_capture_name+"."+link+".capture_linkreset_ROCd").write(0x0)                              
        #dev.getNode(input_link_capture_name+"."+link+".capture_linkreset_ROCt").write(0x0)                              
        #dev.getNode(input_link_capture_name+"."+link+".capture_linkreset_ECONd").write(0x0)                             
        dev.getNode(input_link_capture_name+"."+link+".aquire_length").write(0x1000)
        dev.getNode(input_link_capture_name+"."+link+".fifo_latency").write(0x0)
        dev.dispatch()

    dev.getNode(input_link_capture_name+".global.aquire").write(0)
    dev.getNode(input_link_capture_name+".global.aquire").write(1)
    dev.dispatch()
    time.sleep(0.001)

    dev.getNode(input_link_capture_name+".global.aquire").write(0)
    dev.dispatch()

    reset_roc = dev.getNode("fast-command-fastcontrol-recv-axi-0.counters.link_reset_roct").read()
    dev.dispatch()
    reset_econt = dev.getNode("fast-command-fastcontrol-recv-axi-0.counters.link_reset_econt").read()
    dev.dispatch()
    print('reset roct counters %d'%reset_roc)
    print('reset econt counters %d'%reset_econt)

    for l in range(input_nlinks):
        link = "link%i"%l
        aligned_c = dev.getNode(input_link_capture_name+"."+link+".link_aligned_count").read()
        error_c = dev.getNode(input_link_capture_name+"."+link+".link_error_count").read()
        aligned = dev.getNode(input_link_capture_name+"."+link+".status.link_aligned").read()
        dev.dispatch()
        print('%s %s %d %d %d'%(input_link_capture_name,link, aligned, aligned_c, error_c))
        
        fifo_occupancy = dev.getNode(input_link_capture_name+"."+link+".fifo_occupancy").read()
        dev.dispatch()
        if fifo_occupancy>0:
            data = dev.getNode(input_bram_name+"."+link).readBlock(int(fifo_occupancy))
            dev.dispatch()
            print('fifo occupancy %s %d %i' %(link,fifo_occupancy,len(data)))
            if l==0:                                                                                                   
                print(link)                                                                                                
                print([hex(i) for i in data])                                                                              
        dev.getNode(input_link_capture_name+"."+link+".aquire").write(0x0)
        dev.getNode(input_link_capture_name+"."+link+".explicit_rstb_acquire").write(0x0)
        dev.getNode(input_link_capture_name+"."+link+".explicit_rstb_acquire").write(0x1)
        dev.dispatch()
    dev.getNode(input_link_capture_name+".global.interrupt_enable").write(0x0)
    dev.dispatch()
