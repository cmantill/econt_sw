# ECON-T P1 Testing

## Resets
- Can send and release a reset with:
  ```
  python testing/uhal/reset_signals.py --reset [soft,hard] --i2c [ASIC,emulator]
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
  ```
  # Board 2 (48)
  source scripts/inputWordAlignment.sh 4 4 7,6,7,7,7,8,7,8,8,8,8,8
  # Board 1 (45) 
  source scripts/inputWordAlignment.sh 4 4 7,7,8,8,8,9,8,9,8,9,8,9
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

## To capture data:

   Main script is `testing/uhal/capture.py`, for example:
   ```
   # for input link capture:
   python testing/uhal/capture.py --lc lc-input --mode BX --bx 0 --capture --nwords 511
   
   ```