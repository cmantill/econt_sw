# ECON-T P1 Testing

## Resets
- Can send and release a reset with:
  ```
  python testing/reset_signals.py --reset [soft,hard] --i2c [ASIC,emulator]
  ```
- Sending repeated resets:
  ```
  python testing/reset_signals.py --reset soft --time 0.1 --repeat 10
  ```

## Start-up

- Start i2c servers in hexacontroller:
  ```
  cd zmq_i2c/
  source startServers.sh
  ```
  - This bash script does the following:
  ```
  # start server for ASIC
  python zmq_server.py --addr 0x20 --server 5554
  # start server for emulator
  python zmq_server.py --addr 0x21 --server 5555
  ```

- Initialize ASIC:
  ```
  ./scripts/startUp.sh
  ```
  -  This bash script does the following:
   * Checks all registers in ASIC.
     ```
     python testing/i2c.py --yaml configs/init.yaml
     ```
   * Locks pll manually. This sets `ref_clk_sel, fromMemToLJCDR_enableCapBankOverride, fromMemToLJCDR_CBOvcoCapSelect`.
     It should change `pll_read_bytes_2to0_lfLocked 0x1` and PUSM state to 8 (`STATE_WAIT_CHNS_LOCK`).
     ```
     python testing/i2c.py --name PLL_ref_clk_sel,PLL_enableCapBankOverride,PLL_CBOvcoCapSelect --value 1,1,100
     ```
   * Checks Power-Up-State-Machine.
     ```
     python testing/i2c.py --name PUSM_state
     ```
   * Configures IO (with `invert` option selected):
     ```
     source env.sh
     python testing/align_on_tester.py --step configure-IO --invertIO
     ```
   * Resets fast commands, sets input clock to 40MHz, sends bit transitions with 28 bit PRBS (in the test vectors block).
     ```
     python testing/align_on_tester.py --step init 
     ```
     This should change ` misc_ro_0_PUSM_state 0x9` (`STATE_FUNCTIONAL`).
   * Finally, sets run bit in ASIC:
     ```
     python testing/i2c.py --name MISC_run --value 1
     ```

## Alignment

### Word and phase alignment
  Most used configuration:
  ```
  source scripts/inputWordAlignment.sh 3 3 BESTPHASE
  ```

  -  For board 3 (48):
  ```
  source scripts/inputWordAlignment.sh 3 3 6,13,7,14,14,0,7,8,7,7,7,8

  BESTPHASE (PRBS w best setting, thr 500) = 6,13,7,14,14,0,7,8,7,7,7,8
  BESTPHASE (PRBS w min errors) = 7,6,0,7,7,0,0,0,7,0,0,0
  BESTPHASE (scan hdr_mm_cntr) = 7,6,7,7,7,8,7,8,8,8,8,8
  ```

  - For board 2 (45)
  ```
  BESTPHASE (PRBS w best setting, thr 500) =
  BESTPHASE (PRBS w min errors) = 
  BESTPHASE (scan hdr_mm_cntr) = 7,7,8,8,8,9,8,9,8,9,8,9
  ```
  
  - To keep the same trackMode use BESTPHASE=0.
 
  - Set up the alignment registers. Make sure they are set for both ASIC and emulator
    ```
    python testing/i2c.py --yaml configs/align.yaml --write --i2c ASIC,emulator
    ```
  - Manually configure phase using `phaseSelect` and `trackMode=0`. You can use the values of `phaseSelect` found in the hdr_mm_cntr or prbs_chk_err_cnt scan per channel.
    ```
    python testing/i2c.py --name EPRXGRP_TOP_trackMode --value 0
    python testing/i2c.py --name CH_EPRXGRP_[0-11]_phaseSelect --value $PHASESELECT
    ```  
  Once you are confident on phase-alignment:
  - Send link reset ROC-T at a given BX BXLR. And set the DELAY for the emulator.
    ```
    python testing/align_on_tester.py --step lr-roct --delay DELAY --bxlr BXLR
    ```
  - Read the snapshot,select registers on the ASIC:
    ```
    python testing/i2c.py --yaml configs/align_read.yaml
    ```

    For the `ASIC` to be word-aligned:
    * The `9cccccccaccccccc` matching pattern needs to appear in the snapshot
    * `select` can take values of [0x20,0x3f] (inclusive).
    * `status` needs to be 0x3

  - If the `9cccccccaccccccc` matching pattern is not appearing in the snapshot, try changing:
    ```
    python testing/i2c.py --name ALIGNER_orbsyn_cnt_load_val,ALIGNER_orbsyn_cnt_snapshot --value X,X
    python testing/align_on_tester.py --step lr-roct
    python testing/i2c.py --yaml configs/align_read.yaml
    ```

  - Once the ASIC is aligned and you have found the values for `orbsyn_cnt_snapshot` and `orbsyn_cnt_load_val`, set the same for the emulator (by default the same).
    You can use `delay` to find the delay of getting data to the ASIC
    ```
    python testing/i2c.py --name ALIGNER_orbsyn_cnt_load_val,ALIGNER_orbsyn_cnt_snapshot --value X,X --i2c emulator
    python testing/uhal/align_on_tester.py --step lr-roct --delay X --bxlr 3500 
    python testing/i2c.py --yaml configs/align_read.yaml --i2c emulator
    ```
  
    For the `emulator` to be word-aligned:
    - Make sure that the last words of the snapshot are: `9cccccccaccccccc` (7 c's!).
    - `select` must be `0x20`.
    - `status` will be `0x2`.

  - You can check the alignment by using:
    ```
    python testing/eRx.py --alignment --verbose
    ```

  - You can log in hdr mis-match counters (should be estable with good phase alignment), with:
    ```
    python testing/eRx.py --logging -N 1 --sleep 2
    ```

### IO alignment
  ```
  source scripts/ioAlignment.sh 
  ```

  - Set to threshold sum with maximum threshold value and send zero-data.
    The threshold sum is already configured by default in `configs/align.yaml`.
    ```
    python testing/i2c.py --name MFC_ALGORITHM_SEL_DENSITY_algo_select --value 0 --i2c ASIC,emulator 
    python testing/i2c.py --name ALGO_threshold_val_[0-47] --value 4194303 --i2c ASIC,emulator 
    ```
    Then, configure IO and send zero-data:
    ```
    python testing/align_on_tester.py --step configure-IO --invertIO
    # send zero-data
    python testing/eRx.py --tv --dtype zeros
    ```
    To check alignment:
    ```
    python testing/check_block.py --check --block from-IO
    ```
    To print eye width and registers:
    ```
    python testing/check_block.py --block from-IO
    ```
    Once automatic alignment works, one can set to manual delay mode:
    ```
    python testing/align_on_tester.py --step manual-IO    
    ```

### ASIC Link capture alignment
  ```
  source scripts/lcAlignment.sh
  ```

  - Set the sync word and send a link reset econ-t
    ```
    python testing/i2c.py --name FMTBUF_tx_sync_word --value 0x122
    python testing/align_on_tester.py --step lr-econt
    ```
  - You can check if lc-ASIC is aligned using:
    ```
    python testing/check_block.py --check --block lc-ASIC
    ```
    Note: With `Dec3` and `Dec9` versions of firmware we do not expect lc-ASIC to have status aligned

    * To capture data with a link reset ROCT
    ```
    python testing/eTx.py --capture --lc lc-ASIC --mode linkreset_ECONt --capture --csv
    ```

- ASIC link capture and emulator link capture alignment
  ```
  source scripts/lcEmulatorAlignment.sh 
  ```
  - To modify the latency. This finds the latency for each elink in the link capture such that the BX0 appears in the same spot.
    It does it first for the ASIC, then for the emulator, both should find the BX0 word at the same row.
    ```
    python testing/align_on_tester.py --step latency
    ```
  - To check the number of words that agree.
    ```
    python testing/eTx.py --compare --sleep 1 --nlinks 13
    ```

## Quick setup (if FPGA is set up)
```
source scripts/quickASICSetup.sh $BOARD
```
where $BOARD = 2 (45), 3(48)

(Assumes that FC stream, BCR are enabled)
- Locks FC by configuring when FC clock locks to data
- Locks PLL by configuring PLL VCR capacitor value
- Fixed-mode phase alignment with known "best" settings from PRBS scan
- Manual word alignment with known `sel` value
- Sets threshold algorithm with high thresholds, and zero IDLE word
- Sets run bit to 1
- Reads PUSM state

Note that it does not configure IO and it can be used when power cycle the ASIC or do a hard reset but leave the FPGA configuration untouched.

## ERX and Input data
   ### To modify the input test vectors
   - With an output produced by elink outputs:
   ```
   python testing/eRx.py --tv --dtype ((PRBS,PRBS32,PRBS28,zeros)
   ```
   - With input test vectors in `idir`:
   ```
   python testing/eRx.py --tv --idir $IDIR
   ```

   ### Phase alignment
   - To log `hdr_mm_cntr`:
   ```
   python testing/eRx.py --logging --sleep 120 -N 10
   ```
   - To check `hdr_mm_cntr`:
   ```
   python testing/eRx.py --hdrMM
   ```
   - To manually take a snapshot at a fixed BX:
   ```
   python testing/eRx.py --snapshot --bx 4 
   ```
   - To scan `hdr_mm_cntr` after manually changing phase:

   ### Inversion
   - Test inverting ERX from IO block and with i2c registers:
   ```
   # to-IO block (default is with --invertIO)
   python testing/uhal/align_on_tester.py --step configure-IO --io_names to
   # i2c (change values to 1 to invert)
   python testing/i2c.py --name ERX_ch_*_invert_data --value 0 --quiet
   # check snapshot
   python testing/eRx.py --snapshot
   ```
  
## ETX and Output data

   - To capture data:
   ```
   # for input link capture:
   python testing/eTx.py --capture --lc lc-input --mode BX --bx 0 --capture --nwords 511 --csv --verbose
   # for output link captures, e.g:
   python testing/eTx.py --capture --lc lc-ASIC,lc-emulator --mode BX --bx 0 --capture --nwords 10
   ```
   - To compare data in ASIC and emulator link captures:
   ```
   python testing/eTx.py --compare --sleep 1 --nlinks 13
   ```
   
   ### PLL_phase_of_enable_1G28 Scan
   - To scan PLL_phase_of_enable_1G28 while sending zeros and just scan headers (assuming 0 is good Phase that you want to go back to):
   ```
   python testing/eTx.py --scan --good 0 --bx 40 --nwords 100
   ```
   
   ### Data comparison and acquisition
   - Can be used to:
      - load new registers and input test vectors
      - compare outputs between ASIC and emulator
      - trigger on a mismatch and print out first rows

   1. To do comparison without changing test vector inputs or i2c registers
   ```
   python testing/eTx.py --daq
   ```
   2. To change the test vectors using a default data type e.g. zeros w headers
   ```
   python testing/eTx.py --daq --dtype zeros
   ```
   3. To load new test vectors from directory (this will change the i2c registers using the yaml file init.yaml in that directory),
   - e.g. `IDIR = configs/test_vectors/counterPatternInTC/RPT/`.
   ```
   python testing/eTx.py --daq --idir configs/test_vectors/counterPatternInTC/RPT/
   ```
   - To keep the i2c registers unmodified for both ASIC and emulator:
   ```
   python testing/eTx.py --daq --idir configs/test_vectors/counterPatternInTC/RPT/ --i2ckeep
   ```
   - To modify the i2c registers of only one of the ECONs:
   ```
   python testing/eTx.py --daq --idir configs/test_vectors/counterPatternInTC/RPT/ --i2ckeys ASIC # or, emulator
   ```
   4. For triggering on mistmatches, capturing data and saving it into files
   ```
   python testing/eTx.py --daq --idir configs/test_vectors/counterPatternInTC/RPT/ --trigger 
   ```
   
   ### Using pre-determined test-vectors
   The general testing procedure is:
   ```
   # load the pre-determined test-vectors in $dir, enable triggering on mismatches
   python testing/eTx.py --daq --idir $dir --trigger
   # capture output in lc-ASIC as a record
   python testing/eTx.py --capture --fname $(basename $dir) --verbose
   ```

   This is summarized in:
   ```
   source scripts/compareEmulator.sh $IDIR
   ```

   - To Test the the test dataset `TS_diffThreshold`:
     This sets different threshold levels for the ASIC and the Emulator, at a targeted level, such that a single BX will be different between the two.
     ```
     # modify the input dataset and the ASIC i2c parameters but do not compare yet:
     python testing/eTx.py --daq --idir configs/test_vectors/randomPatternExpInTC/TS_diffThreshold/ --nocompare --yaml init_ASIC --i2ckeys ASIC
     # modify the input dataset and the emulator i2c parameters (From a different yaml file) but do not compare yet:
     python testing/eTx.py --daq --idir configs/test_vectors/randomPatternExpInTC/TS_diffThreshold/ --nocompare --yaml init_emulator --i2ckeys emulator
     # modify the input dataset, keep the i2c configuration for the ASIC and emulator and do the comparison (and trigger on mis-match):
     python testing/eTx.py --daq --idir configs/test_vectors/randomPatternExpInTC/TS_diffThreshold/ --i2ckeep --trigger
     ```

## Fast commands
   - Introduce delay in FC data:
   ```
   python testing/fast_command.py --fc command-delay
   ```
   - Chip sync
   ```
   python testing/fast_command.py --fc chipsync
   ```
   - To read, e.g:
   ```
   python testing/fast_command.py --fc chipsync --read
   ```
