from unpack_utils import *
import numpy as np
import pandas as pd
import bitstring
import argparse
from functools import partial
parser = argparse.ArgumentParser()
parser.add_argument('-i', type=str, required=True, dest="inputFile", help="input file")
parser.add_argument('-n', type=int, required=True, dest="n_TX_enabled",help="number of etx enabled")
parser.add_argument('--header', dest="header", action='store_true', default=False, help='Input file has header')
parser.add_argument('--algo', type=str, required=True, dest="algo", choices=["TS","RPT","BC","AE","input"], help="algorithm to unpack")
parser.add_argument('--nrows', type=int, default=1, dest="nrows", help="number of rows")
parser.add_argument('--startrow', type=int, default=0, dest="startrow", help="initial row to read")
args = parser.parse_args()

"""
For reading HEX files with headers.
"""

if args.algo=="input":
    nlinks = 12
    x_names = ['RX_DATA_%i'%i for i in range(nlinks)]
else:
    nlinks = 13
    x_names = ['TX_DATA_%i'%i for i in range(nlinks)]

converters = dict.fromkeys(x_names)
for key in converters.keys():
    converters[key] = partial(int, base=16)
    
if args.header:
    df = pd.read_csv(args.inputFile, converters=converters)[args.startrow:args.nrows]
else:
    df = pd.read_csv(args.inputFile,header=None,names=x_names,converters=converters)[args.startrow:args.nrows]

if args.algo!="input":
    df = df.iloc[:, :args.n_TX_enabled]
        
# convert to np array
data_bxs = df.to_numpy(dtype=np.dtype(np.uint32)).flatten()

# convert to bytes
data_raw = b"".join([bitstring.BitArray(uint=d,length=32).bytes for d in data_bxs])

# unpack data
if args.algo=='TS':
    data_rows = TS_unpack(data_raw)
elif args.algo=='RPT':
    data_rows = Repeater_unpack(data_raw,args.n_TX_enabled)
elif args.algo=='STC':
    data_rows = STC_unpack(data_raw,args.n_TX_enabled)
elif args.algo=='BC':
    data_rows = BC_unpack(data_raw,args.n_TX_enabled)
elif args.algo=='AE':
    data_rows = AE_unpack(data_raw,args.n_TX_enabled)
elif args.algo=='input':
    data_rows = Input_unpack(data_raw)
else:
    print('no selected algo')
    exit

for i,d in enumerate(data_rows):
    print(i,d['BX'],d['Charge'])
    # charge encoded with 4E+3M
