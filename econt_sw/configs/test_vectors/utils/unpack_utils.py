import bitstruct
import numpy as np

possible_headers = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,31]
possible_headers_input = [9,10]
possible_headers_fixedlat = [0,1,2,3,4,5,6,7,15]

def Input_unpack(data):
    offset = 0
    rows = []
    neRx = 12
    try:
        while True:
            charges = []
            for i in range(neRx):
                # 4-bit header
                header, = bitstruct.unpack_from('u4', data, offset=offset)
                offset += bitstruct.calcsize('u4')

                assert (header in possible_headers_input), f'Bad BX {header}'

                # 4 TC per eRx (48 Total)
                NTCQ = 4
                charge = np.array(bitstruct.unpack_from('u7'*NTCQ, data, offset=offset))
                charges.extend(list(charge))
                offset += 7*NTCQ

            rows.append({'BX'      : header,
                         'Charge'  : charges})

    except bitstruct.Error:
        print('bitstruct error - offset',offset)
        pass
    return rows

def Repeater_unpack(data,neTx=13):
    offset = 0
    rows = []
    nTC = 48
    try:                
        while True:
            # 5-bit header
            header, = bitstruct.unpack_from('u5', data, offset=offset)
            offset += bitstruct.calcsize('u5')

            assert (header in possible_headers), print(f'Bad BX {header}')

            # 7 bit charge
            charge = np.array(bitstruct.unpack_from('u7'*48, data, offset=offset))
            offset += bitstruct.calcsize('u7'*48)

            # 16 bit words * 2 * number of eTX - (nTC * 7bit + header)
            padding_bits = (16*2*neTx) - (nTC*7 + 5)
            if padding_bits > 0:
                padding = bitstruct.unpack_from(f'u{padding_bits}', data, offset=offset)
                offset += padding_bits
                
            rows.append({'BX'      : header,
                         'Charge'  : charge})

            expBX = ((header + 1) % 16) if (header != 31) else 1
            nextBX,_ = bitstruct.unpack_from('u5', data, offset=offset)
            if nextBX == 31 and expBX == 12:
                print(f'Reached BC0 from {header} to {nextBX}, expected {expBX}')
            elif nextBX != expBX:
                print(f'Wrong BX progression from {header} to {nextBX}, expected {expBX}')

    except:
        print('bitstruct error - offset',offset)
        pass
    return rows
            
def TS_unpack(data):
    offset = 0
    rows = []
    try:
        while True:
            start_offset = offset

            # sum can be sum of all 48 TC or the sum of non-transmitted TC
            header = bitstruct.unpack_from_dict('u5u3u8', ['BX', 'Type', 'Sum'], data, offset=offset)
            offset += bitstruct.calcsize('u5u3u8')

            assert (header['BX'] in possible_headers), f"Bad BX {header['BX']}"
            
            if header['Type'] == 0b100: # high occupancy
                # print('high occupancy')
                # 3 words of channel map
                addr = np.array(bitstruct.unpack_from('b1'*48, data, offset=offset), bool)
                offset += bitstruct.calcsize('b1'*48)
                NTCQ = sum(addr)
                # 7-bit charge
                charge = np.array(bitstruct.unpack_from('u7'*NTCQ, data, offset=offset))
                offset += 7*NTCQ
                # 22 16 bit words - NTCQ * (7 bit charge)
                padding_bits = (22*16 - NTCQ*7) 
                if padding_bits > 0:
                    padding = bitstruct.unpack_from(f'u{padding_bits}', data, offset=offset)
                    offset += padding_bits
                else:
                    padding = None
                rows.append({'BX'      : header['BX'],
                             'Type'    : header['Type'],
                             'Sum'     : header['Sum'],
                             'Addr'    : addr,
                             'NTCQ'    : NTCQ,
                             'Charge'  : charge,
                             'Padding' : padding})
            elif header['Type'] == 0b010: # low occupancy
                # print('low occupancy')
                # 3 bit number of TC
                NTCQ, = bitstruct.unpack_from('u3', data, offset=offset)
                offset += 3
                # 6 bit address for each TC
                addr = np.array(bitstruct.unpack_from('u6'*NTCQ, data, offset=offset))
                offset += NTCQ*6
                # 7 bit charge for each TC
                charge = np.array(bitstruct.unpack_from('u7'*NTCQ, data, offset=offset))
                offset += NTCQ*7
                # 25 16 bit words - ((NTCQ bits) + NTCQ * (6 bit addr + 7 bit charge))
                padding_bits = (25*16 - (3 + NTCQ*13))
                if padding_bits > 0:
                    padding = bitstruct.unpack_from(f'u{padding_bits}', data, offset=offset)
                    offset += padding_bits
                else:
                    padding = None
                rows.append({'BX'      : header['BX'],
                             'Type'    : header['Type'],
                             'Sum'     : header['Sum'],
                             'Addr'    : addr,
                             'NTCQ'    : NTCQ,
                             'Charge'  : charge,
                             'Padding' : padding})
            elif header['Type'] in (0b000, 0b110, 0b111): # Zero occupancy or two types of truncated frame
                if header['Type']==0b000: 
                    print('zero')
                elif header['Type']==0b110: 
                    print('from T1 truncation', 'Bx ', header['BX'], ' sum ',header['Sum'])
                elif header['Type']==0b111:
                    print('from T2 or T3 truncation', 'Bx ', header['BX'], ' sum ',header['Sum'])
                rows.append({'BX'      : header['BX'],
                             'Type'    : header['Type'],
                             'Sum'     : header['Sum'],
                             'Addr'    : None,
                             'NTCQ'    : 0,
                             'Charge'  : None,
                             'Padding' : None})

            # Now move past any idle words
            N_idles = 0
            sync_words = []
            expBX = ((header['BX'] + 1) % 16) if (header['BX'] != 31) else 1
            while True:
                nextBX, = bitstruct.unpack_from('u5', data, offset=offset)
                if nextBX == header['BX']:
                    N_idles += 1
                    sync_words.append(bitstruct.unpack_from('u11', data, offset = offset+5))
                    offset += 16
                else:
                    rows[-1]['N_idles'] = N_idles
                    rows[-1]['Sync_words'] = sync_words
                    break

            if nextBX == 31 and expBX == 12:
                print(f'Reached BC0 from {header["BX"]} to {nextBX}, expected {expBX}')
            elif nextBX != expBX:
                print(f'Wrong BX progression from {header["BX"]} to {nextBX}, expected {expBX}')
                offset = start_offset + 16
                rows = rows[:-1]
                continue
            
    except bitstruct.Error:
        print('bitstruct error - offset',offset)
        rows[-1]['N_idles'] = N_idles
        rows[-1]['Sync_words'] = sync_words
        pass
    return rows

def STC_unpack(data,STC_type,neTx):
    """
    Super Trigger Cell: Sums charge data from groups of adjacent 22-bit TC, transmits the sum.
    The index of TC comes from the TC MUX.
    Also transmit the address of the TC with maximum charge in each group when selected.
    data:  data with only neTx active
    STC_type:
    - 0: STC4_9 (5E+4M) Sums of 4 TC
    - 1: STC16_9 (5E+4M) Sums of 16 TC
    - 2: CTC4_7 (4E+3M) Sums of 4 TC
    - 3: STC4_7 (4E+3M) Sums of 4 TC
    """
    offset = 0
    rows = []

    try:
        NSTC = {
            0: [2,5,8,11,12],
            1: [2,3],
            2: [4,8,12],
            3: [3,6,10,12],
        }[STC_type][neTx-1]
    except:
        print(f'Invalid neTx index {neTx-1} for STC_type {STC_type}')
        return rows
    try:
        while True:
            start_offset = offset

            header = bitstruct.unpack_from_dict('u4', ['BX'], data, offset=offset)
            offset += bitstruct.calcsize('u4')
            
            assert (header['BX'] in possible_headers_fixedlat), f"Bad BX {header['BX']}"

            map_size = 0
            if STC_type==0 or STC_type==3:
                # address of the TC with maximum charge
                addr = np.array(bitstruct.unpack_from('u2'*NSTC, data, offset=offset))
                offset += bitstruct.calcsize('u2'*NSTC)
                map_size = NSTC*2
            elif STC_type==1:
                addr = np.array(bitstruct.unpack_from('u4'*NSTC, data, offset=offset))
                offset += bitstruct.calcsize('u4'*NSTC)
                map_size = NSTC*4
            elif STC_type==2:
                addr = None
                
            # 9 bit charge sum for each STC
            charge = np.array(bitstruct.unpack_from('u9'*NSTC, data, offset=offset))
            offset += NSTC*9

            # padding bits
            padding_bits = neTx*2*16 - NSTC*9 - 4 - map_size
            if padding_bits > 0:
                padding = bitstruct.unpack_from(f'u{padding_bits}', data, offset=offset)
                offset += padding_bits
            else:
                padding = None

            rows.append({'BX'      : header['BX'],
                         'Addr'    : addr,
                         'NSTC'    : NSTC,
                         'Charge'  : charge,
                         'Padding' : padding})

            expBX = ((header['BX'] + 1) % 8) if (header['BX'] != 15) else 1
            nextBX, = bitstruct.unpack_from('u4', data, offset=offset)
            if nextBX == 15:
                print(f'Reached BC0 from {header["BX"]} to {nextBX}, expected {expBX}')
            elif nextBX != expBX:
                print(f'Wrong BX progression from {header["BX"]} to {nextBX}, expected {expBX}')
                
    except bitstruct.Error:
        print('bitstruct error - offset',offset)
        pass
    return rows
            
def BC_unpack(data,neTx):
    """
    Best Choice: Sorts the TC by charge and transmits the N TC with highest charge.
    data: data with only neTx active
    """
    offset = 0
    rows = []

    # number of TC to be transmitted by neTx
    NTCQ = {
        1: 1,
        2: 4,
        3: 6,
        4: 9,
        5: 14,
        6: 18,
        7: 23,
        8: 28,
        9: 32,
        10: 37,
        11: 41,
        12: 46,
        13: 48,
    }[neTx]
    
    try:
        while True:
            start_offset = offset

            # if use_sum=1: send sum of all TC in module sum
            header = bitstruct.unpack_from_dict('u4u8', ['BX', 'Sum'], data, offset=offset)
            offset += bitstruct.calcsize('u4u8')

            assert (header['BX'] in possible_headers_fixedlat), f"Bad BX {header['BX']}"

            # addr/map correspond to the position on the output of the channel multiplexer
            map_size = 0
            if NTCQ>=4:
                addr = np.array(bitstruct.unpack_from('b1'*48, data, offset=offset))
                offset += bitstruct.calcsize('b1'*48)
                map_size = 48
            else:
                addr = np.array(bitstruct.unpack_from('b6'*NTCQ, data, offset=offset))
                offset += bitstruct.calcsize('b6'*NTCQ)
                map_size = NTCQ*6

            # 7 bit charge for each NTC
            charge = np.array(bitstruct.unpack_from('u7'*NTCQ, data, offset=offset))
            offset += NTCQ*7

            # padding bits
            padding_bits = neTx*2*16 - NTCQ*7 - 4 - 8 - map_size
            if padding_bits > 0:
                padding = bitstruct.unpack_from(f'u{padding_bits}', data, offset=offset)
                offset += padding_bits
            else:
                padding = None
            rows.append({'BX'      : header['BX'],
                         'Sum'     : header['Sum'],
                         'Addr'    : addr,
                         'NTCQ'    : NTCQ,
                         'Charge'  : charge,
                         'Padding' : padding})

            expBX = ((header['BX'] + 1) % 8) if (header['BX'] != 15) else 1
            nextBX, = bitstruct.unpack_from('u4', data, offset=offset)
            if nextBX == 15:
                print(f'Reached BC0 from {header["BX"]} to {nextBX}, expected {expBX}')
            elif nextBX != expBX:
                print(f'Wrong BX progression from {header["BX"]} to {nextBX}, expected {expBX}')
                
    except bitstruct.Error:
        print('bitstruct error - offset',offset)
        pass
    return rows

def AE_unpack(data,neTx):
    """
    Encoder algorithm
    Weights are programmable by weights in AUTOENCODER_*INPUT block.
    144-bit mask is programmable by mask_ae[143:0].
    """
    offset = 0
    rows = []
    
    try:
        while True:
            start_offset = offset

            # sum uses 5E+4M encoding without dropping any LSB
            header = bitstruct.unpack_from_dict('u5u9', ['BX', 'Sum'], data, offset=offset)
            offset += bitstruct.calcsize('u5u9')

            assert (header in possible_headers), print(f'Bad BX {header}')

            # packed bits
            # here, only N bits are taken from the 144=16*9 encoded bits (9-bit 16 encoded outputs).
            # N is determined from the number of 1s in mask_ae
            # the first encoded[:packed_bits] are transmitted, packed_bits depends on neTx
            # is up to the user that packed_bits>N
            packed_bits = neTx*2*16 - 5 -9
            packed_data = bitstruct.unpack_from(f'u{packed_bits}', data, offset=offset)
            offset += packet_bits

            rows.append({'BX'      : header['BX'],
                         'Sum'     : header['Sum'],
                         'Charge'  : packed_data,
                         'Padding' : None})

            expBX = ((header['BX'] + 1) % 16) if (header['BX'] != 31) else 1
            nextBX, = bitstruct.unpack_from('u4', data, offset=offset)
            if nextBX == 31 and expBX == 12:
                print(f'Reached BC0 from {header["BX"]} to {nextBX}, expected {expBX}')
            elif nextBX != expBX:
                print(f'Wrong BX progression from {header["BX"]} to {nextBX}, expected {expBX}')
                                
    except bitstruct.Error:
        print('bitstruct error - offset',offset)
        pass
    return rows
