#!/usr/bin/env python3

from econ_i2c import econ_i2c
i2c = econ_i2c(1)

translate = True
if translate:
    from translator import Translator
    translator = Translator('ECON-T')
    
    # Read all default registers into a default dict
    default = translator.pairs_from_cfg()
    
    # Load test map and expand config
    paramMap = translator.load_param_map("../configs/init_align.yaml")['ECON-T']
    pairs = translator.pairs_from_cfg(paramMap)
    
    # Read previous values of addresses in test map
    writeCaches = {}
    for addr,vals in pairs.items():
        size_byte = vals[1]
        readback = i2c.read(0x21, addr, size_byte)
        '''
        if size_byte == 1:
            print("Prev value: ",hex(addr), "0x%02x"%tuple(readback))
        elif size_byte == 2:
            print("Prev value: ",hex(addr), "0x%02x%02x"%tuple(readback[::-1]))
        else:
            pass
        print(readback)
        '''
        writeCaches[addr] = readback
        
    # Now get new default values for those registers
    pairs = translator.pairs_from_cfg(paramMap,writeCaches)

    # Convert those pairs into a config
    #cfg = translator.cfg_from_pairs(pairs)

    # Write and Read
    pairs_read = {}
    for addr,vals in pairs.items():
        val = vals[0]
        size_byte = vals[1]
        #print(hex(addr), hex(int.from_bytes(vals[0],'little')), vals[1], vals[0])
        i2c.write(0x20, addr, val)
        readback = i2c.read(0x20, addr, vals[1])
        pairs_read[addr] = [readback, size_byte]

    print(pairs_read)
    # Print
    cfg = translator.cfg_from_pairs(pairs_read)
    for access,accessDict in cfg.items():
        for block,blockDict in accessDict.items():
            for param, paramDict in blockDict.items():
                print(access,block, param, hex(cfg[access][block][param]))

else:
    TX_en = 13
    Use_sum = 0
    STC_type = 0
    i2c.write(0x20, 0x03a9 + 0x7, [((TX_en & 0xf) << 4) | ((Use_sum & 0x1) << 2) | (STC_type & 0x3)])
    readback = i2c.read(0x20, 0x03a9 + 0x7, 1)
    print('FMTBUF_ALL config: ', "0x%02x"%tuple(readback))

    # Output buffer threshold T1
    Buff_T1 = 52 # This must be at least 52 for the econ-t emulator to work
    i2c.write(0x20, 0x03a9 + 0x02, Buff_T1.to_bytes(2, 'little'))
    readback = i2c.read(0x20, 0x03a9 + 0x02, 2)
    print("FMTBUF_ALL buff_t1: ", "0x%02x%02x"%tuple(readback[::-1])) 
    
    # Set the maximum bunch counter value to 3563, the number of bunch crossings in one orbit (minus one)
    BX_max = 3563
    i2c.write(0x20, 0x0380 + 0x12, BX_max.to_bytes(2, 'little'))
    readback = i2c.read(0x20, 0x0380 + 0x12, 2)
    print("ALIGNER_ALL orbsyn_cnt_max_val: ","0x%02x%02x"%tuple(readback[::-1]))
    
    # Set the bunch counter value on an orbit sync fast command to 0 --- but maybe this should not be 0? (JSW)
    orbsyn_val = 1 # Needs to be 1 to test STC
    i2c.write(0x20, 0x0380 + 0x14, orbsyn_val.to_bytes(2, 'little'))
    readback = i2c.read(0x20, 0x0380 + 0x14, 2)
    print("ALIGNER_ALL orbsyn_cnt_load_val: ", "0x%02x%02x"%tuple(readback[::-1]))
    
    # Set the bunch counter value on which to take a snapshot to 4.  This needs to be set so that the
    # special BX0 sync pattern from the HGCROC will appear inside the snapshot.
    orbsyn_snap = 4
    i2c.write(0x20, 0x0380 + 0x16, orbsyn_snap.to_bytes(2, 'little'))
    readback = i2c.read(0x20, 0x0380 + 0x16, 2)
    print("ALIGNER_ALL orbsyn_cnt_snapshot: ", "0x%02x%02x"%tuple(readback[::-1]))
    
    # Set the match pattern and mask for the word aligner
    patt_BX1 = 0xaccccccc
    patt_BX0 = 0x9ccccccc
    match_val = (patt_BX0 << 32) | patt_BX1
    i2c.write(0x20, 0x380 + 0x1, match_val.to_bytes(8, 'little'))
    readback = i2c.read(0x20, 0x380 + 0x1, 8)
    print("ALIGNER_ALL match_pattern_val: ", hex(int.from_bytes(readback, 'little')))
    
    match_mask = 0x0000000000000000
    i2c.write(0x20, 0x380 + 0x9, match_mask.to_bytes(8, 'little'))
    readback = i2c.read(0x20, 0x380 + 0x9, 8)
    print("ALIGNER_ALL match_mask_val: ", hex(int.from_bytes(readback, 'little')))
    
    # Enable snapshot_arm [bit 0], and snapshot_en [bit 1] but do not enable i2c_snapshot_en [bit 2] nor dbg_fc_cnt_clr [bit 3]
    i2c.write(0x20, 0x0380, [0b00000011])
    readback = i2c.read(0x20, 0x0380, 1)
    print("ALIGNER_ALL config: ", hex(int.from_bytes(readback, 'little')))
    
    # Turn on automatic alignment for all links
    for i in range(12):
        i2c.write(0x20, 0x0000 + 0x00 + 0x40*i, [0b00000001])
        readback = i2c.read(0x20, 0x0000 + 0x00 + 0x40*i, 1)
        print("CH_ALIGNER_%i_ALL config: "%i,  hex(int.from_bytes(readback, 'little')))
