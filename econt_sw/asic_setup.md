# ECON-T P1 Testing

## Start-up

- Start i2c server in hexacontroller:
```
# for ASIC
python3 zmq_server.py --addr 0x20 --server 5554
# for emulator
python3 zmq_server.py --addr 0x21 --server 5555
```

- Initialize ASIC:
  ```
  ./start_up.sh
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
     python testing/uhal-align_on_tester.py --step configure-IO --invertIO
     ```
   * Resets fast commands, sets input clock to 40MHz, sends bit transitions with PRBS (in the test vectors block).
     ```
     python testing/uhal-align_on_tester.py --step init 
     ```
     This should change ` misc_ro_0_PUSM_state 0x9` (`STATE_FUNCTIONAL`).
   * Finally, sets run bit in ASIC:
     ```
     python3 testing/i2c.py --name MISC_run --value 1
     ```

## Resets
- Can send and release a reset with:
  ```
  python testing/uhal-reset_signals.py --reset [soft,hard] --i2c [ASIC,emulator]
  ```

## Alignment

- i2c registers
  - Set up the alignment registers.
    Make sure they are set for both ASIC and emulator
    ```
    python3 testing/i2c.py --yaml configs/align.yaml --write --i2c ASIC,emulator
    ```

- Word alignment:
  - Send link reset ROC-T.
    ```
    python testing/uhal-align_on_tester.py --step lr-roct 
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
    python testing/uhal-align_on_tester.py --step lr-roct
    python3 testing/i2c.py --yaml configs/align_read.yaml
    ```

  - Once the ASIC is aligned and you have found the values for `orbsyn_cnt_snapshot` and `orbsyn_cnt_load_val`, set the same for the emulator (by default the same).
    You can use `delay` to find the delay of getting data to the ASIC
    ```
    python3 testing/i2c.py --name ALIGNER_orbsyn_cnt_load_val,ALIGNER_orbsyn_cnt_snapshot --value X,X --i2c emulator
    python testing/uhal-align_on_tester.py --step lr-roct --delay X
    python3 testing/i2c.py --yaml configs/align_read.yaml --i2c emulator
    ```
  
    For the `emulator` to be word-aligned:
    - Make sure that the last words of the snapshot are: `9cccccccaccccccc` (7 c's!).
    - `select` must be `0x20`.
    - `status` will be `0x2`.

- IO alignment
  - Set to threshold sum with maximum threshold value and send zero-data.
    The threshold sum is already configured by default in `configs/align.yaml`.
    ```
    python3 testing/i2c.py --name MFC_ALGORITHM_SEL_DENSITY_algo_select --value 0 --i2c ASIC,emulator 
    python3 testing/i2c.py --name ALGO_threshold_val_[0-47] --value 4194303 --i2c ASIC,emulator 
    ```
    Then, configure IO and send zero-data:
    ```
    python testing/uhal-align_on_tester.py --step configure-IO --invertIO
    # send zero-data
    python testing/uhal-align_on_tester.py --step test-data
    python testing/uhal-align_on_tester.py --step check-IO
    ```

- Link capture alignment

  - Send a link reset econ-t
    ```
    python testing/uhal-align_on_tester.py --step lr-econt
    ```
  - You can check if lc-ASIC is aligned using:
    ```
    python testing/uhal-align_on_tester.py --step check-lcASIC
    ```
    Note: With `Dec3` and `Dec9` versions of firmware we do not expect lc-ASIC to have status aligned,
    * To capture data with a link reset ROCT
    ```
    python testing/uhal-align_on_tester.py --step capture --lc lc-ASIC --mode linkreset_ECONt
    ```

  - Align, ASIC link capture and emulator link capture
    ```
    # this finds the latency for each elink in the link capture such that the BX0 appears in the same spot 
    # it does it first for the ASIC, then for the emulator
    # both should find the BX0 word at the same row
    python testing/uhal-align_on_tester.py --step latency

  - To check the number of words that agree.
    If errors > 0, we will issue a L1A and link capture will save data.
    ```
    python testing/uhal-align_on_tester.py --step compare
    ```

## To take data:

- To test a test vector dataset you can use `eventDAQ.py`. This script will load i2c registers and then capture data with a L1A.
  ```
  python3 testing/eventDAQ.py --idir  configs/test_vectors/XXX/XXX --capture l1a
  ```

- Alternatively to just load a dataset and capture on L1A (without changing i2c registers):
  ```
  python testing/uhal-eventDAQ.py --idir configs/test_vectors/XXX/XXX --capture l1a
  ```