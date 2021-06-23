from TS_unpack import TS_unpack
import numpy as np
import pandas as pd

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('-i', type=str, default='zmq_i2c/Buffer_TS.csv', dest="inputFile",
                    help="input file")
parser.add_argument('-n', type=int, default=2, dest="n_TX_enabled")
parser.add_argument('--sim', action='store_true', default=False, dest='sim')
args = parser.parse_args()

if args.sim:
    df = pd.read_csv(args.inputFile)
    df = df.iloc[:, :args.n_TX_enabled]
else:
    df = pd.read_csv(args.inputFile,header=None,skiprows=list(range(0,7)))
    df = df[:40]

# convert to np array
data_bxs = df.to_numpy(dtype=np.dtype(np.uint32))

# convert to bytes
data_raw = np.frombuffer(np.ascontiguousarray(data_bxs), dtype=np.dtype(np.uint16)).byteswap().tobytes()

# unpack data taken with TS algorithm
data_rows = TS_unpack(data_raw)
