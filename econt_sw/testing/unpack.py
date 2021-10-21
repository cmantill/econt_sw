from functools import partial
from unpack_utils import TS_unpack,Repeater_unpack
import numpy as np
import pandas as pd
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('-i', type=str, required=True, dest="inputFile", help="input file")
parser.add_argument('-n', type=int, default=13, dest="n_TX_enabled")
parser.add_argument('--sim', action='store_true', default=False, dest='Input file from emulation')
parser.add_argument('--algo', type=str, required=True, dest="algo", choices=["TS","repeater"], help="algorithm to unpack")
parser.add_argument('--nrows', type=int, default=10, dest="nrows", help="number of rows")
args = parser.parse_args()

"""
For reading HEX files.
"""

noutput_links = 13
etx_names = ['TX_DATA_%i'%i for i in range(13)]
converters = dict.fromkeys(etx_names)
for key in converters.keys():
    converters[key] = partial(int, base=16)

if args.sim:
    df = pd.read_csv(args.inputFile, converters=converters)
    df = df.iloc[:, :args.n_TX_enabled]
else:
    df = pd.read_csv(args.inputFile,header=None,names=etx_names,converters=converters)

# select number of rows
df = df[:args.nrows]

# convert to np array
data_bxs = df.to_numpy(dtype=np.dtype(np.uint8))

# convert to bytes
data_raw = np.frombuffer(np.ascontiguousarray(data_bxs), dtype=np.dtype(np.uint16)).byteswap().tobytes()

# unpack data
if args.algo=='TS':
    data_rows = TS_unpack(data_raw)
elif args.algo=='repeater':
    data_rows = Repeater_unpack(data_raw)
else:
    print('no selected algo')
    exit
    
for d in data_rows:
    print(d['BX'])
