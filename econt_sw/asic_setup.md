# ECON-T P1 Testing

## Resets
- Can send and release a reset with:
  ```
  python testing/uhal/reset_signals.py --reset [soft,hard] --i2c [ASIC,emulator]
  ```

## Quick setup
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

## Start-up

- Start i2c servers in hexacontroller:
  ```
  cd zmq_i2c/
  source startServers.sh
  ```
  - This bash script does the following:
  ```
  # start server for ASIC
  python3 zmq_server.py --addr 0x20 --server 5554
  # start server for emulator
  python3 zmq_server.py --addr 0x21 --server 5555
  ```

- Initialize ASIC:
  ```
  ./scripts/startUp.sh
  ```
  -  This bash script does the following:
   * Checks all registers in ASIC.
     ```
     python3 testing/i2c.py --yaml configs/init.yaml
     ```
   * Locks pll manually. This sets `ref_clk_sel, fromMemToLJCDR_enableCapBankOverride, fromMemToLJCDR_CBOvcoCapSelect`.
     It should change `pll_read_bytes_2to0_lfLocked 0x1` and PUSM state to 8 (`STATE_WAIT_CHNS_LOCK`).
     ```
     python3 testing/i2c.py --name PLL_ref_clk_sel,PLL_enableCapBankOverride,PLL_CBOvcoCapSelect --value 1,1,100
     ```
   * Checks Power-Up-State-Machine.
     ```
     python3 testing/i2c.py --name PUSM_state
     ```
   * Configures IO (with `invert` option selected):
     ```
     source env.sh
     python testing/uhal/align_on_tester.py --step configure-IO --invertIO
     ```
   * Resets fast commands, sets input clock to 40MHz, sends bit transitions with 28 bit PRBS (in the test vectors block).
     ```
     python testing/uhal/align_on_tester.py --step init 
     ```
     This should change ` misc_ro_0_PUSM_state 0x9` (`STATE_FUNCTIONAL`).
   * Finally, sets run bit in ASIC:
     ```
     python3 testing/i2c.py --name MISC_run --value 1
     ```

## Alignment

### Word and phase alignment
  For example:
  ```
  source scripts/inputWordAlignment.sh 4 4 BESTPHASE
  ```

  For board 3 (48):
  ```
  BESTPHASE (PRBS w best setting, thr 500) = 6,13,7,14,14,0,7,8,7,7,7,8
  BESTPHASE (PRBS w min errors) = 7 6 0 7 7 0 0 0 7 0 0 0
  BESTPHASE (scan hdr_mm_cntr) = 
  ```

  For board 2 (45)
  ```
  BESTPHASE = 
  ```

  - Set up the alignment registers.
    Make sure they are set for both ASIC and emulator
    ```
    python3 testing/i2c.py --yaml configs/align.yaml --write --i2c ASIC,emulator
    ```
  - Manually configure phase using `phaseSelect` and `trackMode=0`. You can use the values of `phaseSelect` found in the hdr_mm_cntr or prbs_chk_err_cnt scan per channel.
    ```
    python3 testing/i2c.py --name EPRXGRP_TOP_trackMode --value 0
    python3 testing/i2c.py --name CH_EPRXGRP_[0-11]_phaseSelect --value $PHASESELECT
    ```  
  Once you are confident on phase-alignment:
  - Send link reset ROC-T.
    ```
    python testing/uhal/align_on_tester.py --step lr-roct 
    ```
  - Read the snapshot,select registers on the ASIC:
    ```
    python3 testing/i2c.py --yaml configs/align_read.yaml
    ```

    For the `ASIC` to be word-aligned:
    * The `9cccccccaccccccc` matching pattern needs to appear in the snapshot
    * `select` can take values of [0x20,0x3f] (inclusive).
    * `status` needs to be 0x3

  - If the `9cccccccaccccccc` matching pattern is not appearing in the snapshot, try changing:
    ```
    python3 testing/i2c.py --name ALIGNER_orbsyn_cnt_load_val,ALIGNER_orbsyn_cnt_snapshot --value X,X
    python testing/uhal/align_on_tester.py --step lr-roct
    python3 testing/i2c.py --yaml configs/align_read.yaml
    ```

  - Once the ASIC is aligned and you have found the values for `orbsyn_cnt_snapshot` and `orbsyn_cnt_load_val`, set the same for the emulator (by default the same).
    You can use `delay` to find the delay of getting data to the ASIC
    ```
    python3 testing/i2c.py --name ALIGNER_orbsyn_cnt_load_val,ALIGNER_orbsyn_cnt_snapshot --value X,X --i2c emulator
    python testing/uhal/align_on_tester.py --step lr-roct --delay X --bxlr 3500 
    python3 testing/i2c.py --yaml configs/align_read.yaml --i2c emulator
    ```
  
    For the `emulator` to be word-aligned:
    - Make sure that the last words of the snapshot are: `9cccccccaccccccc` (7 c's!).
    - `select` must be `0x20`.
    - `status` will be `0x2`.

  - You can check the alignment by using:
    ```
    python3 testing/eRxMonitoring.py --alignment --verbose
    ```

  - You can log in hdr mis-match counters (should be estable with good phase alignment), with:
    ```
    python3 testing/eRxMonitoring.py --logging -N 1 --sleep 2
    ```

### IO alignment
  ```
  source scripts/ioAlignment.sh 
  ```

  - Set to threshold sum with maximum threshold value and send zero-data.
    The threshold sum is already configured by default in `configs/align.yaml`.
    ```
    python3 testing/i2c.py --name MFC_ALGORITHM_SEL_DENSITY_algo_select --value 0 --i2c ASIC,emulator 
    python3 testing/i2c.py --name ALGO_threshold_val_[0-47] --value 4194303 --i2c ASIC,emulator 
    ```
    Then, configure IO and send zero-data:
    ```
    python testing/uhal/align_on_tester.py --step configure-IO --invertIO
    # send zero-data
    python testing/uhal/test_vectors.py --dtype zeros
    ```
    To check alignment:
    ```
    python testing/uhal/check_align.py --check --block from-IO
    ```
    To print eye width and registers:
    ```
    python testing/uhal/check_align.py --block from-IO
    ```
    Once automatic alignment works, one can set to manual delay mode:
    ```
    python testing/uhal/align_on_tester.py --step manual-IO    
    ```

### ASIC Link capture alignment
  ```
  source scripts/lcAlignment.sh
  ```

  - Set the sync word and send a link reset econ-t
    ```
    python3 testing/i2c.py --name FMTBUF_tx_sync_word --value 0x122
    python testing/uhal/align_on_tester.py --step lr-econt
    ```
  - You can check if lc-ASIC is aligned using:
    ```
    python testing/uhal/check_align.py --check --block lc-ASIC
    ```
    Note: With `Dec3` and `Dec9` versions of firmware we do not expect lc-ASIC to have status aligned

    * To capture data with a link reset ROCT
    ```
    python testing/uhal/capture.py --lc lc-ASIC --mode linkreset_ECONt --capture
    ```

- ASIC link capture and emulator link capture alignment
  ```
  source scripts/lcEmulatorAlignment.sh 
  ```
  - To modify the latency. This finds the latency for each elink in the link capture such that the BX0 appears in the same spot.
    It does it first for the ASIC, then for the emulator, both should find the BX0 word at the same row.
    ```
    python testing/uhal/align_on_tester.py --step latency
    ```

  - To check the number of words that agree.
    ```
    python testing/uhal/align_on_tester.py --step compare
    ```

## ERX and Input data
   ### To modify the input test vectors
   - With an output produced by elink outputs:
   ```
   python testing/uhal/test_vectors.py --dtype (PRBS,PRBS32,PRBS28,zeros) 
   ```
   - With input test vectors in `idir`:
   ```
   python testing/uhal/test_vectors.py --idir $IDIR
   ```

   ### Phase alignment
   - To log `hdr_mm_cntr`:
   ```
   python3 testing/eRxMonitoring.py --logging --sleep 120 -N 10
   ```
   - To check `hdr_mm_cntr`:
   ```
   python3 testing/eRxMonitoring.py --hdrMM
   ```
   - To manually take a snapshot at a fixed BX:
   ```
   python3 testing/eRxMonitoring.py --snapshot --bx 4 
   ```
   - To scan `hdr_mm_cntr` after manually changing phase:
  
## ETX and Output data

   - Main script is `testing/uhal/capture.py`, for example:
   ```
   # for input link capture:
   python testing/uhal/capture.py --lc lc-input --mode BX --bx 0 --capture --nwords 511
   # for output link capture 
   python testing/uhal/capture.py --lc lc-ASIC --mode BX --bx 0 --capture --nwords 10
   # for emulator link capture
   python testing/uhal/capture.py --lc lc-emulator --mode BX --bx 0 --capture --nwords 10        
   ```
   - Using capture in eTxMonitoring
   ```
   # for output link capture on ASIC:
   python3 testing/eTxMonitoring.py --capture --verbose --nwords 12
   ```
   - Using compare:
   ```
   python testing/uhal/capture.py --compare --sleep 1 --nlinks 13
   ```

### PLL_phase_of_enable_1G28 Scan
    - To scan PLL_phase_of_enable_1G28 while sending zeros and just scan headers (assuming 0 is good Phase that you want to go back to):
    ```
    python3 testing/eTxMonitoring.py --scan --bx 40 --nwords 100 --goodPhase 0
    ```

## Fast commands
   - Introduce delay in FC data:
   ```
   python testing/uhal/fast_command.py --fc command-delay
   ```
