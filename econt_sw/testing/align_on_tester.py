import uhal
import time
import argparse
import numpy

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE, NONE",default='NONE')
    args = parser.parse_args()

    if args.logLevel.find("ERROR")==0:
        uhal.setLogLevelTo(uhal.LogLevel.ERROR)
    elif args.logLevel.find("WARNING")==0:
        uhal.setLogLevelTo(uhal.LogLevel.WARNING)
    elif args.logLevel.find("NOTICE")==0:
        uhal.setLogLevelTo(uhal.LogLevel.NOTICE)
    elif args.logLevel.find("DEBUG")==0:
        uhal.setLogLevelTo(uhal.LogLevel.DEBUG)
    elif args.logLevel.find("INFO")==0:
        uhal.setLogLevelTo(uhal.LogLevel.INFO)
    else:
        uhal.disableLogging()

    man = uhal.ConnectionManager("file://connection.xml")
    dev = man.getDevice("mylittlememory")

    names = {
        'IO': {'to': "ASIC-IO-IO-to-ECONT-ASIC-IO-blocks-0",
               'from': "ASIC-IO-IO-from-ECONT-ASIC-IO-blocks-0"},
        'testvectors': {'switch': "test-vectors-to-ASIC-and-emulator-test-vectors-ipif-switch-mux",
                        'stream': "test-vectors-to-ASIC-and-emulator-test-vectors-ipif-stream-mux",
                        'bram': "test-vectors-to-ASIC-and-emulator-test-vectors-out-block00-bram-ctrl"
                    },
        'bypass': {'switch': "econt-emulator-bypass-option-expected-outputs-RAM-ipif-switch-mux",
                   'stream': "econt-emulator-bypass-option-expected-outputs-RAM-ipif-stream-mux"
               },
        'fc': 'housekeeping-FastControl-fastcontrol-axi-0',
    }
    input_nlinks = 12
    output_nlinks = 13

    # send PRBS
    for l in range(input_nlinks):
        link = "link%i"%l
        dev.getNode(testvectors_switch_name+"."+link+".output_select").write(0x1)
    dev.dispatch()

    raw_input("Sending PRBS. Press key to continue...")

    # configure IO blocks
    for io,io_name in names['IO'].items():
        nlinks = input_nlinks if io=='to' else output_nlinks
        for l in range(nlinks):
            link = "link%i"%l
            dev.getNode(io_name+"."+link+".reg0.tristate_IOBUF").write(0x0)
            dev.getNode(io_name+"."+link+".reg0.bypass_IOBUF").write(0x0)
            dev.getNode(io_name+"."+link+".reg0.invert").write(0x0)
            dev.getNode(io_name+"."+link+".reg0.reset_link").write(0x0)
            dev.getNode(io_name+"."+link+".reg0.reset_counters").write(0x1)
            if io=='to':
                dev.getNode(io_name+"."+link+".reg0.delay_mode").write(0x0)
            else:
                dev.getNode(io_name+"."+link+".reg0.delay_mode").write(0x1)
        dev.getNode(io_name_to+".global.global_rstb_links").write(0x1)
        dev.dispatch()

    # check from-IO is aligned
    for l in range(output_nlinks):
        while True:
            link = "link%i"%l
            bit_tr = dev.getNode(names['IO']['from']+"."+link+".reg3.waiting_for_transitions").read()
            delay_ready = dev.getNode(names['IO']['from']+"."+link+".reg3.delay_ready").read()
            dev.dispatch()
            print("%s: bit_tr %d and delay ready %d"%(link,bit_tr,delay_ready))
            if delay_ready==1:
                break

    # setup normal output
    out_brams = []
    for l in range(input_nlinks):
        link = "link%i"%l
        names['testvectors']['switch']
        dev.getNode(names['testvectors']['switch']+"."+link+".output_select").write(0x0)
        dev.getNode(names['testvectors']['switch']+"."+link+".n_idle_words").write(255)
        # dev.getNode(names['testvectors']['switch']+"."+link+".n_idle_words").write(0)
        dev.getNode(names['testvectors']['switch']+"."+link+".idle_word").write(0xaccccccc)
        dev.getNode(names['testvectors']['switch']+"."+link+".idle_word_BX0").write(0x9ccccccc)
        # dev.getNode(names['testvectors']['switch']+"."+link+".idle_word_BX0").write(0xabcd1234)
        dev.getNode(names['testvectors']['switch']+"."+link+".header_mask").write(0xf0000000)
        dev.getNode(names['testvectors']['switch']+"."+link+".header").write(0xa0000000)
        dev.getNode(names['testvectors']['switch']+"."+link+".header_BX0").write(0x90000000)

        # size of bram is 4096
        out_brams.append([None] * 4096)
        
        dev.getNode(names['testvectors']['stream']+"."+link+".sync_mode").write(0x1)
        dev.getNode(names['testvectors']['stream']+"."+link+".ram_range").write(0x1)
    dev.dispatch()

    # check that settings are as expected
    for l in range(input_nlinks):
        osel = dev.getNode(names['testvectors']['switch']+"."+link+".output_select").read()
        nwords = dev.getNode(names['testvectors']['switch']+"."+link+".n_idle_words").read()
        idle = dev.getNode(names['testvectors']['switch']+"."+link+".idle_word").read()
        idlebx0 =  dev.getNode(names['testvectors']['switch']+"."+link+".idle_word_BX0").read()
        header_mask = dev.getNode(names['testvectors']['switch']+"."+link+".header_mask").read()
        header = dev.getNode(names['testvectors']['switch']+"."+link+".header").read()
        header_BX0 = dev.getNode(names['testvectors']['switch']+"."+link+".header_BX0").read()
        dev.dispatch()
        if l==0:
            print('osel %d, nwords %d, idle %02x, idlebx0 %02x, header_mask %02x, header %02x, header_BX0 %02x'%(osel,nwords,idle,idlebx0,header_mask,header,header_BX0))
        sync = dev.getNode(names['testvectors']['stream']+"."+link+".sync_mode").read()
        ram = dev.getNode(names['testvectors']['stream']+"."+link+".ram_range").read()
        force_sync =  dev.getNode(names['testvectors']['stream']+"."+link+".force_sync").read()
        dev.dispatch()
        if l==0:
            print('sync %d, ram %d, force_sync %d '%(sync,ram,force_sync))

    # set zero-data with headers
    for l in range(input_nlinks):
        for i,b in enumerate(out_brams[l]):
            if i==0: out_brams[l][i] = 0x90000000
        else:
            out_brams[l][i] = 0xa0000000
            #out_brams[l][i] = 0xa0000000+i
        dev.getNode(names['testvectors']['bram'].replace('00',"%02d"%l)).writeBlock(out_brams[l])
        dev.dispatch()
        time.sleep(0.001)

    # send link reset roct
    # this would align the emulator on the ASIC board and the emulator on the tester board simultaneously
    dev.getNode(names['fc']+".command.enable_fast_ctrl_stream").write(0x1);
    dev.getNode(names['fc']+".command.enable_orbit_sync").write(0x1);

    # set BXs
    dev.getNode(names['fc']+".bx_link_reset_roct").write(3500)
    dev.getNode(names['fc']+".bx_link_reset_rocd").write(3501)
    dev.getNode(names['fc']+".bx_link_reset_econt").write(3502)
    dev.getNode(names['fc']+".bx_link_reset_econd").write(3503)

    # configure bypass
    for l in range(output_nlinks):
        link = "link%i"%l
        dev.getNode(bypass_switch_name+"."+link+".output_select").write(0x1)
    dev.dispatch()
