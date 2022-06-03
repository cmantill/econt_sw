Input data contains rotating counters in each of the trigger cell's ADC	value. The counter changes in each BX.
Each counter is 7 bits (to fit in the 7 bits of dat for each TC), rolling over at 128.

| BX | ADC TC_0 | ADC TC_1 | ADC TC_2 | ADC TC_3 |  ... | ADC TC_44 | ADC TC_45 | ADC TC_46 | ADC TC_47 |
|--|--|--|--|--|--|--|--|--|--|
| 0  |        0 |        0 |        0 |        0 |  ... |        0 |        0 |        0 |        0 |
| 1  |        1 |        1 |        1 |        1 |  ... |        1 |        1 |        1 |        1 |
| 2  |        2 |        2 |        2 |        2 |  ... |        2 |        2 |        2 |        2 |
| 3  |        3 |        3 |        3 |        3 |  ... |        3 |        3 |        3 |        3 |
| 4  |        4 |        4 |        4 |        4 |  ... |        4 |        4 |        4 |        4 |
| 5  |        5 |        5 |        5 |        5 |  ... |        5 |        5 |        5 |        5 |