import itertools
import array

def PRBS15(seed):
    x = seed
    while True:
        yield x
        for i in range(32):
            x = ((x << 1) & 0xffffffff) | (((x >> 14) & 1) ^ ((x >> 13) & 1))


prbs15 = list(itertools.islice(PRBS15(0xacb1eba4), 22))

for p in prbs15:
    print(hex(p))
