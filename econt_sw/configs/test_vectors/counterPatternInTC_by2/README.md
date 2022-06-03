Input data contains rotating counters (increasing by 2) in each of the trigger cells ADC value.
Each counter is 7 bits (to fit in the 7 bits of dat for each TC), rolling over at 128.

| BX | ADC TC_0 | ADC TC_1 | ADC TC_2 | ADC TC_3 |  ... | ADC TC_44 | ADC TC_45 | ADC TC_46 | ADC TC_47 |
|--|--|--|--|--|--|--|--|--|--|
| 0  |        0 |        2 |        4 |        6 |  ... |        88 |        90 |        92 |        94	|
| 1  |        1 |        3 |        5 |        7 |  ... |        89 |        91 |        93 |        95	|
| 2  |        2 |        4 |        6 |        8 |  ... |        90 |        92 |        94 |        96	|
| 3  |        3 |        5 |        7 |        9 |  ... |        91 |        93 |        95 |        97	|
| 4  |        4 |        6 |        8 |       10 |  ... |        92 |        94 |        96 |        98	|
| 5  |        5 |        7 |        9 |       11 |  ... |        93 |        95 |        97 |        99 |


#### Test directories
 - **RPT/** Normal setup: repeater algorithm, muxed to correct input order, calibration of 1 everywhere, HDM
 - **RPT_CAL_555/** Test Calibration Bits: calibration set to `0x555`, or ~0.66 for all channels, repeater algorithm, muxed to correct input order, HDM
 - **RPT_CAL_AAA/** Test Calibration Bits: calibration set to `0xAAA`, or ~1.33 for all channels, repeater algorithm, muxed to correct input order, HDM
 - **RPT_LDM/** Test float-to-fixed conversion when in low density module, repeater algorithm, muxed to correct input order, calibration of 1 everywhere
 - **RPT_MUX_[N]/** Test of mux settings, shifts all outputs N to the right (N=1..47) w.r.t. normal **RPT/** setup, repeater algorithm, calibration of 1 everywhere, HDM
