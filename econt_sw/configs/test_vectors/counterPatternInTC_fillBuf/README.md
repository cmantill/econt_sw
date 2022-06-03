Input data contains rotating counters in each of the trigger cell's ADC	value. The counter changes in each BX.
Each counter is 7 bits (to fit in the 7 bits of dat for each TC), rolling over at 128.

| BX | ADC TC_0 | ADC TC_1 | ADC TC_2 | ADC TC_3 |  ... | ADC TC_44 | ADC TC_45 | ADC TC_46 | ADC TC_47 |
|--|--|--|--|--|--|--|--|--|--|
| 0  |        6 |        6 |        6 |        6 |  ... |        6 |        6 |        6 |        6 |
| 1  |        7 |        7 |        7 |        7 |  ... |        7 |        7 |        7 |        7 |
| 2  |        8 |        8 |        8 |        8 |  ... |        8 |        8 |        8 |        8 |
..
The counters stop at BX>100. Then we zero the data.

With HDM, Threshold = 5 (with encoding 4->0 so threshold needs to be > 4).

With 12 eTX:
- We expect buffer to empty in BX=108. Always use Cond4 - full data type.
- T1 high (480). T2/T3 do not matter (because T2>T1 500>480).

With 11 eTX:
- We expect buffer to empty in BX=118. Always use Cond4 - full data type.
- T1 high (480). T2/T3 do not matter (because T2>T1 500>480).

With 10 eTx:
- Emulator fails in BX=94. nbuf+nbxc=(460+25) = 485> (len buf = 480).
- T1 high (480). T2/T3 do not matter (because T2>T1 500>480).
- If len buf > 480:
  - We expect buffer to use truncated type in BX=94.
  - And to empty in BX=127.

With 10 eTx:
- T1 higher (505). T2/T3 do not matter (because T2>T1 510>505).
- If len buf = 506:
  - We will overflow at BX=98: nbuf+nbxc=(480+25)
  - And at Bx=99: nbuf+nbxc=(485+25) - we should lose 5 words?
