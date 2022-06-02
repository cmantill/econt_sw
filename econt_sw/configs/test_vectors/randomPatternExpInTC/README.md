Input data contains random trigger cell data from an exponential. TC data is bounded at 127 (7 bit).

| BX |  ADC_TC_0 | ADC_TC_1 | ADC_TC_2 | ADC_TC_3  | ...  | ADC_TC_44 | ADC_TC_45 | ADC_TC_46 | ADC_TC_47 |
|--|--|--|--|--|--|--|--|--|--|
| 0  |       6   |     16   |      1   |     32    | ...  |         0 |         5 |        12 |         5 |
| 1  |      14   |     19   |     14   |     12    | ...  |        31 |        13 |         4 |        20 |
| 2  |       3   |      7   |     16   |     27    | ...  |         4 |         5 |         9 |         7 |
| 3  |       5   |      0   |     40   |     12    | ...  |         8 |        76 |         2 |         3 |
| 4  |       1   |     11   |      6   |     21    | ...  |        19 |         3 |        46 |         1 |

The dataset is generated with exponential spectrum, such that the full range of ADC values is covered.

The test dataset **TS_diffThreshold** sets different threshold levels for the ASIC and the Emulator, at a  targeted level, such that a single BX will be different between the two.  In the input dataset, a single BX has a value of 53 in ADC_TC_0.  To introduce a difference, the threshold are set for all channels at 3456 (the decoded value corresponding to ADC=53 in a high density module), but in the emulator, the threshold for channel 0 is set to 3457.  This will cause the cell in channel 0 to fail the threshold in the emulator, but pass it in the ASIC.


