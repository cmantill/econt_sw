from utils.test_vectors import TestVectors

tv=TestVectors()

import numpy as np

#pattern=np.array([list(range(3564))*12]).reshape(12,-1)

pattern=np.array([0xe335a5a]*12*3564).reshape(12,-1)
#pattern=np.array([0xe335c5c]*12*3564).reshape(12,-1)

#pattern=np.array([0]*12*3564).reshape(12,-1)
#pattern[:,np.arange(0,3564,4)]=0xfffffff

pattern[:,1:] += 0xa << 28
pattern[:,0] += 0x9 << 28


tv.configure(dtype='pattern',pattern=pattern)
