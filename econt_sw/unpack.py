from TS_unpack import TS_unpack
import numpy as np

data_str = """0x849efa37,0xc388fc21"""

n_TX_enabled = 2

# convert string to np array
data_bxs = []
for row in data_str.split('\n'):
    data_bxs.append([int(d,0) for d in row.split(',')[:n_TX_enabled]])
data_bxs = np.array(data_bxs, dtype=np.dtype(np.uint32))

# convert to bytes
data_raw = np.frombuffer(data_bxs.data, dtype=np.dtype(np.uint16)).byteswap().tobytes()

# unpack data taken with TS algorithm
data_rows = TS_unpack(data_raw)

print(data_rows)
