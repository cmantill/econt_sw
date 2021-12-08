# ECON-T P1 Testing

## Start-up:

- Start a server
```
# for ASIC
python3 zmq_server.py --addr 0x20 --server 5554
# for emulator
python3 zmq_server.py --addr 0x21 --server 5555
```

- To check all registers in ASIC:
```
source check_all.sh 
```

- To lock pll manually in ASIC:
```
source pll_manual.sh
```
This sets: `ref_clk_sel, fromMemToLJCDR_enableCapBankOverride, fromMemToLJCDR_CBOvcoCapSelect`.
And should change `pll_read_bytes_2to0_lfLocked 0x1`.
Then it should be in PUSM_state (8): `STATE_WAIT_CHNS_LOCK`

- Then, configure IO and send bit transitions:
```
source env.sh
python testing/uhal-align_on_tester.py --step configure-IO --invertIO
python testing/uhal-align_on_tester.py --step prbs-data 
```
This should change ` misc_ro_0_PUSM_state 0x9` (`STATE_FUNCTIONAL`).

- Then, set run bit in ASIC:
```
python3 testing/i2c_single_register.py --name MISC_run --value 1
```

## Alignment:

- First, set up the alignment registers 
```
# for ASIC
source align_set.sh
# for emulator
source align_set_emulator.sh
```
This sets:
```
ASIC: 
orbsyn_cnt_load_val: 0 # bunch counter value on an orbit sync fast command
orbsyn_cnt_snapshot: 3 # bunch counter value on which to take a snapshot
Emulator:
orbsyn_cnt_load_val: 0
orbsyn_cnt_snapshot: 3
```

- Then, send link reset ROC-T.
This also sends zeroes with headers and sets up the delay for emulator.
```
python testing/uhal-align_on_tester.py --step lr-roct 
```

- Then, read the registers:
```
source align_read.sh
source align_read_emulator.sh
```

- If the `9cccccccaccccccc` matching pattern is not appearing in the snapshot you can try changing the registers, then sending another link-reset-ROCT and reading again, e.g.:
```
python3 testing/i2c_single_register.py --name ALIGNER_orbsyn_cnt_load_val,ALIGNER_orbsyn_cnt_snapshot --value X,X
python testing/uhal-align_on_tester.py --step lr-roct
source align_read.sh
```

- Once you see the alignment pattern in the snapshot and status aligned:
For ASIC:
```
RO CH_ALIGNER_0INPUT_ALL snapshot 0xffffffffffffffffcccccccaccccccc9cccccccaccccccca
RO CH_ALIGNER_0INPUT_ALL status 0x3
RO CH_ALIGNER_1INPUT_ALL snapshot 0xffffffffffffffffcccccccaccccccc9cccccccaccccccca
RO CH_ALIGNER_1INPUT_ALL status 0x3
RO CH_ALIGNER_2INPUT_ALL snapshot 0xcccccccacccccccacccccccaccccccc9cccccccaccccccca
RO CH_ALIGNER_2INPUT_ALL status 0x3
RO CH_ALIGNER_3INPUT_ALL snapshot 0xcccccccacccccccacccccccaccccccc9cccccccaccccccca
RO CH_ALIGNER_3INPUT_ALL status 0x3
RO CH_ALIGNER_4INPUT_ALL snapshot 0xcccccccacccccccacccccccaccccccc9cccccccaccccccca
RO CH_ALIGNER_4INPUT_ALL status 0x3
RO CH_ALIGNER_5INPUT_ALL snapshot 0xcccccccacccccccacccccccaccccccc9cccccccaccccccca
RO CH_ALIGNER_5INPUT_ALL status 0x3
RO CH_ALIGNER_6INPUT_ALL snapshot 0xcccccccacccccccacccccccaccccccc9cccccccaccccccca
RO CH_ALIGNER_6INPUT_ALL status 0x3
RO CH_ALIGNER_7INPUT_ALL snapshot 0xffffffffffffffffcccccccaccccccc9cccccccaccccccca
RO CH_ALIGNER_7INPUT_ALL status 0x3
RO CH_ALIGNER_8INPUT_ALL snapshot 0xcccccccacccccccacccccccaccccccc9cccccccaccccccca
RO CH_ALIGNER_8INPUT_ALL status 0x3
RO CH_ALIGNER_9INPUT_ALL snapshot 0xcccccccacccccccacccccccaccccccc9cccccccaccccccca
RO CH_ALIGNER_9INPUT_ALL status 0x3
RO CH_ALIGNER_10INPUT_ALL snapshot 0xcccccccacccccccacccccccaccccccc9cccccccaccccccca
RO CH_ALIGNER_10INPUT_ALL status 0x3
RO CH_ALIGNER_11INPUT_ALL snapshot 0xffffffffffffffffcccccccaccccccc9cccccccaccccccca
RO CH_ALIGNER_11INPUT_ALL status 0x3
```

- Once you have found the values for `orbsyn_cnt_snapshot` and `orbsyn_cnt_load_val`, e.g. 0,3, set the same for the emulator, and use delay to find the delay of getting data to the ASIC
```
python3 testing/i2c_single_register.py --name ALIGNER_orbsyn_cnt_load_val,ALIGNER_orbsyn_cnt_snapshot --value 0,3 --i2c emulator --addr 1 --server 5555
python testing/uhal-align_on_tester.py --step lr-roct --delay X
source align_read_emulator.sh
```

- You should see the alignment pattern in the snapshot of the emulator (the status will still be 0x2):
```
RO CH_ALIGNER_0INPUT_ALL snapshot 0xffffffffffffffffacccccccaccccccc9cccccccaccccccc
RO CH_ALIGNER_0INPUT_ALL status 0x2
RO CH_ALIGNER_1INPUT_ALL snapshot 0xacccccccacccccccacccccccaccccccc9cccccccaccccccc
RO CH_ALIGNER_1INPUT_ALL status 0x2
RO CH_ALIGNER_2INPUT_ALL snapshot 0xacccccccacccccccacccccccaccccccc9cccccccaccccccc
RO CH_ALIGNER_2INPUT_ALL status 0x2
RO CH_ALIGNER_3INPUT_ALL snapshot 0xacccccccacccccccacccccccaccccccc9cccccccaccccccc
RO CH_ALIGNER_3INPUT_ALL status 0x2
RO CH_ALIGNER_4INPUT_ALL snapshot 0xacccccccacccccccacccccccaccccccc9cccccccaccccccc
RO CH_ALIGNER_4INPUT_ALL status 0x2
RO CH_ALIGNER_5INPUT_ALL snapshot 0xacccccccacccccccacccccccaccccccc9cccccccaccccccc
RO CH_ALIGNER_5INPUT_ALL status 0x2
RO CH_ALIGNER_6INPUT_ALL snapshot 0xacccccccacccccccacccccccaccccccc9cccccccaccccccc
RO CH_ALIGNER_6INPUT_ALL status 0x2
RO CH_ALIGNER_7INPUT_ALL snapshot 0xacccccccacccccccacccccccaccccccc9cccccccaccccccc
RO CH_ALIGNER_7INPUT_ALL status 0x2
RO CH_ALIGNER_8INPUT_ALL snapshot 0xacccccccacccccccacccccccaccccccc9cccccccaccccccc
RO CH_ALIGNER_8INPUT_ALL status 0x2
RO CH_ALIGNER_9INPUT_ALL snapshot 0xacccccccacccccccacccccccaccccccc9cccccccaccccccc
RO CH_ALIGNER_9INPUT_ALL status 0x2
RO CH_ALIGNER_10INPUT_ALL snapshot 0xacccccccacccccccacccccccaccccccc9cccccccaccccccc
RO CH_ALIGNER_10INPUT_ALL status 0x2
RO CH_ALIGNER_11INPUT_ALL snapshot 0xacccccccacccccccacccccccaccccccc9cccccccaccccccc
RO CH_ALIGNER_11INPUT_ALL status 0x2
```

We want to see the snapshot at the same position. It does not have to be exactly the same. 
A leftward shift of less than 32 bits is OK.
A rightward shift is not, because then the ASIC will not be able to align (it has to see the complete 0x9cccccccaccccccc pattern).
Select points at the first bit of 9 in 0x9cccccccaccccccc, right? So we need select in the ASIC to be in the interval [0x20, 0x3f].

- Then, set to threshold sum (by default), set to maximum threshold and send zero-data
```
python3 testing/i2c_single_register.py --name MFC_ALGORITHM_SEL_DENSITY_algo_select --value 0
for i in {0..47}; do python3 testing/i2c_single_register.py --name ALGO_threshold_val_${i} --value 4194303; done;
for i in {0..47}; do python3 testing/i2c_single_register.py --name ALGO_threshold_val_${i} --value 4194303 --i2c emulator --addr 1 --server 5555; done;
python testing/uhal-align_on_tester.py --step configure-IO --invertIO
python testing/uhal-align_on_tester.py --step zero-data 
python testing/uhal-align_on_tester.py --step check-IO
```

- Then, try aligning the ASIC link capture by sending a link reset ECON-T:
```
python testing/uhal-align_on_tester.py --step lr-econt
# check if it is aligned
python testing/uhal-align_on_tester.py --step check-lcASIC
```
- To manually align:
  - Check the output saved in the `check-lcASIC` step: lc-ASIC-alignoutput_debug.csv:
    ```
    f9225922,f9225922,f9225922,f9225922,f9225922,f9225922,f9225922,f9225922,f9225922,f9225922,f9225922,f9225922,f9225922
    0922f922,0922f922,0922f922,0922f922,0922f922,0922f922,0922f922,0922f922,0922f922,0922f922,0922f922,0922f922,0922f922
    ```
  - Manually override the alignment (and modify the snippet with a different delay if needed) with:
    ```
    python testing/uhal-align_on_tester.py --step manual-lcASIC
    python testing/uhal-align_on_tester.py --step manual-lcASIC --alignpos 16
    ```
  - Then check again:
    ```
    python testing/uhal-align_on_tester.py --step check-lcASIC
    ```
    You should have
    ```
    f922f922,f922f922,f922f922,f922f922,f922f922,f922f922,f922f922,f922f922,f922f922,f922f922,f922f922,f922f922,f922f922
    09220922,09220922,09220922,09220922,09220922,09220922,09220922,09220922,09220922,09220922,09220922,09220922,09220922
    ```
- Then, align link captures:
```
python testing/uhal-align_on_tester.py --step capture
python testing/uhal-align_on_tester.py --step compare
```

## To take data:

```
python3 testing/eventDAQ.py --idir  configs/test_vectors/XXX/XXX --capture l1a
# or
python3 testing/eventDAQ.py --idir  configs/test_vectors/XXX/XXX --capture compare
```