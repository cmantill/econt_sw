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
python3 testing/i2c.py --yaml configs/init.yaml
# to check PUSM
python3 testing/i2c.py --name PUSM_state
```

- To lock pll manually in ASIC:
```
python3 testing/i2c.py --name PLL_ref_clk_sel,PLL_enableCapBankOverride,PLL_CBOvcoCapSelect --value 1,1,100
```

This sets: `ref_clk_sel, fromMemToLJCDR_enableCapBankOverride, fromMemToLJCDR_CBOvcoCapSelect`.
And should change `pll_read_bytes_2to0_lfLocked 0x1`.
Then it should be in PUSM_state (8): `STATE_WAIT_CHNS_LOCK`

- Then, configure IO and send bit transitions with PRBS:
```
source env.sh
python testing/uhal-align_on_tester.py --step configure-IO --invertIO
python testing/uhal-align_on_tester.py --step init 
```
This should change ` misc_ro_0_PUSM_state 0x9` (`STATE_FUNCTIONAL`).

- Then, set run bit in ASIC:
```
python3 testing/i2c.py --name MISC_run --value 1
```

## Alignment:

- First, set up the alignment registers 
```
python3 testing/i2c.py --yaml configs/align.yaml --write --i2c ASIC,emulator
```

- Then, send link reset ROC-T.
This also sends zeroes with headers and sets up the delay for emulator.
```
python testing/uhal-align_on_tester.py --step lr-roct 
```

- Then, read the registers on the ASIC:
```
python3 testing/i2c.py --yaml configs/align_read.yaml
```

- If the `9cccccccaccccccc` matching pattern is not appearing in the snapshot you can try changing the registers, then sending another link-reset-ROCT and reading again, e.g.:
```
# orbsyn_cnt_load_val: bunch counter value on an orbit sync fast command
# orbsyn_cnt_snapshot: bunch counter value on which to take a snapshot
python3 testing/i2c.py --name ALIGNER_orbsyn_cnt_snapshot --value X
python testing/uhal-align_on_tester.py --step lr-roct
python3 testing/i2c.py --yaml configs/align_read.yaml
```

- For debugging, you can send a link reset econt and capture the input at the same time with:
```
python testing/uhal-align_on_tester.py --step capture --lc lc-input --mode linkreset_ROCt
```

- If the snapshot is 0, one can try:
- To take the snapshot with the trigger mode and then spy on it:
```
python3 testing/i2c.py --name ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,CH_ALIGNER_*_per_ch_align_en,ALIGNER_snapshot_arm --value 1,1,[0]*12,0 --i2c ASIC
python3 testing/i2c.py --name ALIGNER_snapshot_arm --value 1 --i2c ASIC,emulator
python3 testing/i2c.py --name CH_ALIGNER_*_snapshot --i2c emulator
```
This should show you the data that is going in.
- Otherwise one can try manually:
```
python3 testing/i2c.py --name ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,CH_ALIGNER_*_per_ch_align_en,ALIGNER_snapshot_arm --value 0,1,[0]*12,0 --i2c ASIC
python testing/uhal-align_on_tester.py --step capture --lc lc-input --mode linkreset_ROCt
python3 testing/i2c.py --name CH_ALIGNER_*_snapshot --i2c emulator
```
- Options in elink outputs:
```
# to send a different pattern
python testing/uhal-align_on_tester.py --step test-data --dtype debug
# to send PRBS
python testing/uhal-align_on_tester.py --step test-data --dtype PRBS
# to send zero data
python testing/uhal-align_on_tester.py --step test-data
# to send repeater dataset
python testing/uhal-align_on_tester.py --step test-data --idir configs/test_vectors/counterPatternInTC/RPT/

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

- Once you have found the values for `orbsyn_cnt_snapshot` and `orbsyn_cnt_load_val`, set the same for the emulator, and use delay to find the delay of getting data to the ASIC
```
python3 testing/i2c.py --name ALIGNER_orbsyn_cnt_load_val,ALIGNER_orbsyn_cnt_snapshot --value X,X --i2c emulator
python testing/uhal-align_on_tester.py --step lr-roct --delay X
python3 testing/i2c.py --yaml configs/align_read.yaml --i2c emulator
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
We want to see the snapshot at ~ the same position. It does not have to be exactly the same. 
A leftward shift of less than 32 bits is OK.
A rightward shift is not, because then the ASIC will not be able to align (it has to see the complete 0x9cccccccaccccccc pattern).
The `select` register in the emulator should be such that the `select` register in the ASIC is in the interval [select_emulator, select_emulator+31bits].
In the example above, `select` for ASIC needs to be in the interval [0x20, 0x3f].
The emulator ALWAYS needs to end in `9cccccccaccccccc`.

- Then, set to threshold sum (by default), set to maximum threshold and send zero-data
```
#python3 testing/i2c.py --name MFC_ALGORITHM_SEL_DENSITY_algo_select --value 0 --i2c ASIC,emulator 
#python3 testing/i2c.py --name ALGO_threshold_val_[0-47] --value 4194303 --i2c ASIC,emulator 
python testing/uhal-align_on_tester.py --step configure-IO --invertIO
python testing/uhal-align_on_tester.py --step zero-data 
python testing/uhal-align_on_tester.py --step check-IO
```

- Then, try aligning the ASIC link capture by sending a link reset ECON-T:
```
python testing/uhal-align_on_tester.py --step lr-econt
# check if it is aligned
python testing/uhal-align_on_tester.py --step check-lcASIC
# capture data
python testing/uhal-align_on_tester.py --step capture --lc lc-ASIC
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
    python testing/uhal-align_on_tester.py --step capture --lc lc-ASIC
    ```
    You should have
    ```
    f922f922,f922f922,f922f922,f922f922,f922f922,f922f922,f922f922,f922f922,f922f922,f922f922,f922f922,f922f922,f922f922
    09220922,09220922,09220922,09220922,09220922,09220922,09220922,09220922,09220922,09220922,09220922,09220922,09220922
    ```
- Then, align link captures:
```
# this finds the latency
python testing/uhal-align_on_tester.py --step latency
# then compare
python testing/uhal-align_on_tester.py --step compare
```

## To take data:

```
python3 testing/eventDAQ.py --idir  configs/test_vectors/XXX/XXX --capture l1a
# or
python3 testing/eventDAQ.py --idir  configs/test_vectors/XXX/XXX --capture compare
```

## Taking snapshot:

```
python3 testing/i2c.py --name ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,CH_ALIGNER_*_per_ch_align_en,ALIGNER_snapshot_arm --value 1,1,[0]*12,0 --i2c ASIC,emulator
python3 testing/i2c.py --name ALIGNER_snapshot_arm --value 1 --i2c ASIC,emulator
python3 testing/i2c.py --name CH_ALIGNER_*_snapshot --i2c emulator
```