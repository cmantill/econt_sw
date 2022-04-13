import argparse
from functools import partial
import bitstring
import numpy as np
import pandas as pd
import configs.test_vectors.utils.unpack_utils as upack

parser = argparse.ArgumentParser()
parser.add_argument('--asic', type=str, required=True, dest="asicFile", help="ASIC input file")
parser.add_argument('--emulator', type=str, required=True, dest="emulatorFile", help="emulator input file")
parser.add_argument('-n', type=int, default=13, dest="n_TX_enabled",help="number of etx enabled")
parser.add_argument('--nrows', type=int, default=-1, dest="nrows", help="number of rows")
parser.add_argument('--startrow', type=int, default=0, dest="startrow", help="initial row to read")
args = parser.parse_args()

nlinks = 13
x_names = ['TX_DATA_%i'%i for i in range(nlinks)]

def convert_to_pandas(inputFile,start=0,stop=-1,n_TX_enabled=13):
    converters = dict.fromkeys(x_names)
    for key in converters.keys():
        converters[key] = partial(int, base=16)

    df = pd.read_csv(inputFile, converters=converters)[start:stop].iloc[:, :n_TX_enabled]
    data_bxs = df.to_numpy(dtype=np.dtype(np.uint32)).flatten()
    data_raw = b"".join([bitstring.BitArray(uint=d,length=32).bytes for d in data_bxs])

    df = pd.DataFrame(upack.TS_unpack(data_raw))
    ntcq = df['NTCQ'].unique()[0]
    df[[f'CH{i}' for i in range(ntcq)]] =  pd.DataFrame(df.Charge.tolist(), index=df.index)
    df[[f'Addr{i}' for i in range(ntcq)]] =  pd.DataFrame(df.Addr.tolist(), index=df.index)
    df.drop(columns=['Charge','Sync_words','Padding','Addr'],inplace=True)
    return df

data_ASIC = convert_to_pandas(args.asicFile,args.startrow,args.nrows,args.n_TX_enabled)
data_emulator = convert_to_pandas(args.emulatorFile,args.startrow,args.nrows,args.n_TX_enabled)

print(data_ASIC)
print(data_emulator)

# now find differences
ne_stacked = (data_emulator != data_ASIC).stack()
changed = ne_stacked[ne_stacked]

difference_locations = np.where(data_emulator != data_ASIC)
changed_from = data_emulator.values[difference_locations]
changed_to = data_ASIC.values[difference_locations]
changes = pd.DataFrame({'from': changed_from, 'to': changed_to}, index=changed.index)

print(changes)
print('Number of errors in fields ',len(changes.index))
