import bitstruct
from numpy import array

def TS_unpack(data):
    # An event must start at the beginning of `data`.  We make no effort to correctly find the starting point.
    offset = 0
    rows = []
    try:
        while True:

            header = bitstruct.unpack_from_dict('u5u3u8', ['BX', 'Type', 'Sum'], data, offset=offset)
            offset += bitstruct.calcsize('u5u3u8')

            if header['Type'] == 0b100: # high occupancy
                addr = array(bitstruct.unpack_from('b1'*48, data, offset=offset), bool)
                offset += bitstruct.calcsize('b1'*48)
                NTCQ = sum(addr)
                padding_bits = (21*16 - NTCQ*7) % 16
                charge = array(bitstruct.unpack_from('u7'*NTCQ, data, offset=offset))
                offset += 7*NTCQ
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
                NTCQ, = bitstruct.unpack_from('u3', data, offset=offset)
                offset += 3
                addr = array(bitstruct.unpack_from('u6'*NTCQ, data, offset=offset))
                offset += NTCQ*6
                charge = array(bitstruct.unpack_from('u7'*NTCQ, data, offset=offset))
                offset += NTCQ*7
                padding_bits = (24*16 - (3 + NTCQ*13)) % 16
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
            while True:
                nextBX, = bitstruct.unpack_from('u5', data, offset=offset)
                if nextBX == header['BX']:
                    N_idles += 1
                    sync_words.append(bitstruct.unpack_from('u11', data, offset = offset+5))
                    offset += 16
                else:
                    break
            rows[-1]['N_idles'] = N_idles
            rows[-1]['Sync_words'] = sync_words
    except bitstruct.Error:
        pass
    return rows

