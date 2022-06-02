Input data contains rotating counters in each of the trigger cell's ADC	value. The counter changes in each BX.
Each counter is 7 bits (to fit in the 7 bits of dat for each TC), rolling over at 128.

| BX | ADC TC_0 | ADC TC_1 | ADC TC_2 | ADC TC_3 |  ... | ADC TC_44 | ADC TC_45 | ADC TC_46 | ADC TC_47 |
|--|--|--|--|--|--|--|--|--|--|
| 0  |        6 |        6 |        6 |        6 |  ... |        6 |        6 |        6 |        6 |
| 1  |        7 |        7 |        7 |        7 |  ... |        7 |        7 |        7 |        7 |
| 2  |        8 |        8 |        8 |        8 |  ... |        8 |        8 |        8 |        8 |
..
The counters max out at BX=127 and keep at 127.
The counters stop at BX>450. Then we zero the data.

With HDM, Threshold = 5 (with encoding 4->0 so threshold needs to be > 4).

- Capping T1 at 450:
NeTx 1 2 3 4 5 6 7 8 9 10 11 12
MaxMRL 225 112 75 56 45 37 32 28 25 22 20 18
T1 ~ 448-450

  - TS_Thr5_HDM_12eTx_MRL18_T1432_noT2T3
  - TS_Thr5_HDM_12eTx_MRL18_T1450_noT2T3 (is there any drop of words?) - buffer fills at BX=469
  - TS_Thr5_HDM_12eTx_MRL18_T1460_noT2T3 (is there any drop of words?) - buffer	fills at BX=470

- Using T1 with MRL=12
NeTx 1  2  3  4  5   6   7   8   9   10  11  12
T1   24 48 72 96 120 144 168 192 216 240 264 288

empty_buf_BX ~ 462-463