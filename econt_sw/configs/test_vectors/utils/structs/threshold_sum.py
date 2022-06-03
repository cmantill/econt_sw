from construct import *
from construct.core import evaluate

class CheckVerbose(Check):
    def _parse(self, stream, context, path):
        passed = evaluate(self.func, context)
        if not passed:
            raise CheckError(f"check failed during parsing, expr = {self.func}, context = {context}", path=path)

    def _build(self, obj, stream, context, path):
        passed = evaluate(self.func, context)
        if not passed:
            raise CheckError(f"check failed during building, expr = {self.func}, context = {context}", path=path)


class ValidatorVerbose(Adapter):
    def _encode(self, obj, context, path):
        return obj

    def _decode(self, obj, context, path):
        obj = self._validate(obj, context, path)
        return obj

    def _validate(self, obj, context, path):
        raise NotImplementedError


class DataTypeValidator(ValidatorVerbose):
    def _validate(self, obj, context, path):
        if obj not in DATA_TYPE_MAP.keys():
            raise ValidationError(
                f'{self.subcon} Unknown data type {obj:>03b} in the header, context = {context}, path = {path}')
        return obj


class IdlePatternValidator(ValidatorVerbose):
    def __init__(self, subcon, idle_pattern=None):
        super().__init__(subcon)
        self.idle_pattern = idle_pattern

    def _validate(self, obj, context, path):
        if not isinstance(obj, list):
            obj = [obj]
        idle_pattern = self.idle_pattern
        for idx, d in enumerate(obj):
            for idle_obj in d.idle:
                if idle_pattern is None:
                    idle_pattern = idle_obj.idle_pattern
                else:
                    if idle_obj.idle_pattern != idle_pattern:
                        print(
                            f'{self.subcon} Inconsistent idle pattern found in entry {idx} ({idle_obj.idle_pattern:>011b}={idle_obj.idle_pattern:>03x}),'
                            f' expected ({idle_pattern:>011b}={idle_pattern:>03x}), context = {context}, path = {path}')
                        return obj[:idx]
        if self.idle_pattern is None and idle_pattern is not None:
            print(f'Found idle pattern 0b{idle_pattern:>011b} (0x{idle_pattern:>03x})')
        return obj


class BXValidator(ValidatorVerbose):
    def _validate(self, obj, context, path):
        for idx in range(len(obj) - 1):
            valid = True
            a = obj[idx]
            b = obj[idx + 1]
            if (a.header.bx_header == 31):
                valid = (b.header.bx_header == 1)
            elif (b.header.bx_header == 31):
                valid = (a.header.bx_header == 11)
            else:
                valid = ((a.header.bx_header + 1) % 16 == b.header.bx_header)
            if not valid:
                print(
                    f'{self.subcon} Inconsistent BX between entry {idx} (BX={a.header.bx_header})'
                    f' and entry {idx+1} (BX={b.header.bx_header}), context = {context}, path = {path}')
                return obj[:idx + 1]
        return obj


class ChannelMap(Adapter):
    '''convert channel map to address list, for the high-occupancy data'''

    def __init__(self, subcon, from_left=True, start=0):
        super().__init__(subcon)
        self.from_left = from_left
        self.start = start

    def _decode(self, obj, context, path):
        s = slice(2, None) if self.from_left else slice(None, 1, -1)
        bits = []
        for i, c in enumerate(bin(obj)[s], self.start):
            if c == '1':
                bits.append(i)
        return bits

    def _encode(self, obj, context, path):
        s = ['0'] * self.subcon.length
        for idx in obj:
            idx = idx - self.start
            if not self.from_left:
                idx = -idx - 1
            s[idx] = '1'
        return int(''.join(s), 2)


DATA_TYPE_MAP = {
    'empty': 0b000,
    'low_occupancy': 0b010,
    'high_occupancy': 0b100,
    'truncation_t1': 0b110,
    'truncation_t2t3': 0b111,
}

DataType = DataTypeValidator(Enum(BitsInteger(3), **DATA_TYPE_MAP))

Header = BitStruct(
    'bx_header' / BitsInteger(5),
    'data_type' / DataType,
    'module_sum' / BitsInteger(8),
    CheckVerbose((this.bx_header < 16) | (this.bx_header == 31)),
)

LowOccupancyData = BitStruct(
    'num_tc' / BitsInteger(3),
    'tc_addresses' / Array(this.num_tc, BitsInteger(6)),
    'tc_data' / Array(this.num_tc, BitsInteger(7)),
    Const(0, BitsInteger((16 - ((3 + 13 * this.num_tc) % 16)) % 16))
)

HighOccupancyData = BitStruct(
    'tc_addresses' / ChannelMap(BitsInteger(48)),
    'tc_data' / Array(len_(this.tc_addresses), BitsInteger(7)),
    Const(0, BitsInteger((16 - ((7 * len_(this.tc_addresses)) % 16)) % 16))
)

DATA_MAP = {
    'empty': Pass,
    'low_occupancy': LowOccupancyData,
    'high_occupancy': HighOccupancyData,
    'truncation_t1': Pass,
    'truncation_t2t3': Pass,
}

Idle = BitStruct(
    'bx_header' / BitsInteger(5),
    'idle_pattern' / BitsInteger(11),
    CheckVerbose(this.bx_header == this._.header.bx_header)
)

ThresholdSumPacket = Struct(
    'header' / Header,
    'data' / Switch(this.header.data_type, DATA_MAP, default=Error),
    'idle' / GreedyRange(Idle),
)

ThresholdSum = BXValidator(GreedyRange(ThresholdSumPacket))

x = ThresholdSumPacket.parse(bytes.fromhex('0a34200009aa09aa09aa09aa'))
print(x)
print(ThresholdSumPacket.build(x).hex())

from functools import partial
import pandas as pd
import numpy as	np
import bitstring

nlinks = 13
x_names = ['TX_DATA_%i'%i for i in range(nlinks)]

converters = dict.fromkeys(x_names)
for key in converters.keys():
    converters[key] = partial(int, base=16)
#inputFile = "/Users/cmantill/ECON/ECONT_Testing/sync-repo-48/repo/econt_sw/econt_sw/configs/test_vectors/counterPatternInTC_MRLBuf/TS_Thr5_HDM_12eTx_MRL18_T1460_noT2T3/testOutput.csv"
#inputFile = "/Users/cmantill/ECON/ECONT_Testing/sync-repo-48/repo/econt_sw/econt_sw/configs/test_vectors/counterPatternInTC_fillBuf/TS_Thr5_HDM_10eTx_T1480_noT2T3/lc-ASIC_sc.csv"
inputFile = "/Users/cmantill/ECON/ECONT_Testing/sync-repo-48/repo/econt_sw/econt_sw/configs/test_vectors/randomPatternExpInTC/TS_Thr1/testOutput.csv"
n_TX_enabled = 13
nrows = 10
df = pd.read_csv(inputFile, converters=converters)[0:nrows]
df = df.iloc[:, :n_TX_enabled]

data_bxs = df.to_numpy(dtype=np.dtype(np.uint32)).flatten()
data_raw = b"".join([bitstring.BitArray(uint=d,length=32).bytes for d in data_bxs])

print(data_raw)
x = ThresholdSumPacket.parse(data_raw)
print(x)
