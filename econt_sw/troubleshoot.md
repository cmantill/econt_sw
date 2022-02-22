# Troubleshoot

## Start-up

- If you see `RO FCTRL_ALL status_fc_error 0x1`:
  Try changing edgesel/invert for FC:
  ```
  python testing/i2c.py --name FCTRL_EdgeSel_T1 --value 0
  # and checking again the status registers
  python testing/i2c.py --yaml configs/init.yaml
  ```
  Note: We see this behavior in `Dec9` firmware.

## Alignment

- i2c registers
  - Verify that alignment registers are the set for both ASIC and emulator:
    ```
    python testing/i2c.py --yaml configs/align.yaml --i2c ASIC,emulator
    ```
- Word alignment
  - An example of ASIC aligned:
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


  - If the `9cccccccaccccccc` matching pattern is not appearing in the snapshot you can try changing the registers related to where the snapshot is taken. 
    Then send another link-reset-ROCT and read again.
    The registers related to where the snapshot is taken are:
    - orbsyn_cnt_load_val: bunch counter value on which an orbit sync fast command is sent (also known as BCR - bunch counter reset). The BCR is sent every orbit.
    - orbsyn_cnt_snapshot: bunch counter value on which to take a snapshot.
    What matters for word alignment is the difference between these two registers. 
    For example, values of (0,3) should give the same behavior as (3513,3516).

    Everytime these registers are changed we need to send another link-reset-ROCT
    ```
    python testing/i2c.py --name ALIGNER_orbsyn_cnt_load_val,ALIGNER_orbsyn_cnt_snapshot --value X,X
    python testing/align_on_tester.py --step lr-roct
    python testing/i2c.py --yaml configs/align_read.yaml
    ```
    
    Values that have worked with our ASICs:
    - difference of 3 or larger in bench setup.

  - To read the parameters in the `status` register:
    ```
    python testing/i2c.py --yaml configs/align_read_status.yaml 
    ```
 
  - If you are not able to see the alignment pattern and status is not aligned, look at `phaseSelect` status and set those values to `config_phaseSelect`. Then, set to trackMode to 0, e.g.
    ```
    # read
    python testing/i2c.py --name CH_EPRXGRP_[0-11]_status_phaseSelect 
    # set
    python testing/i2c.py --name CH_EPRXGRP_[0-11]_phaseSelect --value 5,5,6,5,6,6,5,5,5,6,6,6
    python testing/i2c.py --name EPRXGRP_TOP_trackMode --value 0
    # run alignment script again (send link reset ROC-T) - where 4 and 4 were the values of snapshot and delay before
    source scripts/inputWordAlignment.sh 4 4 
    ```
 
  - If you need to capture the input when sending a link-reset-ROCT:
    ```
    python testing/eTx.py --capture --lc lc-input --mode linkreset_ROCt --capture --csv
    ```

  - To force a snapshot:
    * To take the snapshot with the trigger mode and then spy on it:
    ```
    python testing/i2c.py --name ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,CH_ALIGNER_*_per_ch_align_en,ALIGNER_snapshot_arm --value 1,1,[0]*12,0 --i2c ASIC
    python testing/i2c.py --name ALIGNER_snapshot_arm --value 1 --i2c ASIC,emulator
    python testing/i2c.py --name CH_ALIGNER_*_snapshot --i2c emulator
    ```
    * Otherwise one can try manually:
    ```
    python testing/i2c.py --name ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,CH_ALIGNER_*_per_ch_align_en,ALIGNER_snapshot_arm --value 0,1,[0]*12,0 --i2c ASIC
    python testing/eTx.py --capture --lc lc-input --mode linkreset_ROCt --capture --csv
    python testing/i2c.py --name CH_ALIGNER_*_snapshot --i2c emulator
    ```

  - Options to send data in elink outputs:
    ```
    # to send a different pattern
    python testing/eRx.py --tv --dtype debug
    # to send PRBS
    python testing/eRx.py --tv --dtype PRBS
    # to send zero data
    python testing/eRx.py --tv --dtype zeros
    # to send repeater dataset (or any dataset in a directory)
    python testing/eRx.py --tv --idir configs/test_vectors/counterPatternInTC/RPT/
    ```

  - If snapshot is 0:
    - Try checking fc registers, and make sure there is no fc_error (see start-up section):
      ```
      python testing/i2c.py --name FCTRL*
      ```
   
  - `delay` values that have worked for emulator word-alignment:
     - bench testing (48): delay=3.

  - An example of the emulator aligned:
    ```
    RO CH_ALIGNER_0INPUT_ALL select 0x20
    RO CH_ALIGNER_0INPUT_ALL snapshot 0xacccccccaccccccc9cccccccaccccccc
    RO CH_ALIGNER_0INPUT_ALL status 0x2
    RO CH_ALIGNER_10INPUT_ALL select 0x20
    RO CH_ALIGNER_10INPUT_ALL snapshot 0xacccccccaccccccc9cccccccaccccccc
    RO CH_ALIGNER_10INPUT_ALL status 0x2
    RO CH_ALIGNER_11INPUT_ALL select 0x20
    RO CH_ALIGNER_11INPUT_ALL snapshot 0xacccccccaccccccc9cccccccaccccccc
    RO CH_ALIGNER_11INPUT_ALL status 0x2
    RO CH_ALIGNER_1INPUT_ALL select 0x20
    RO CH_ALIGNER_1INPUT_ALL snapshot 0xacccccccaccccccc9cccccccaccccccc
    RO CH_ALIGNER_1INPUT_ALL status 0x2
    RO CH_ALIGNER_2INPUT_ALL select 0x20
    RO CH_ALIGNER_2INPUT_ALL snapshot 0xacccccccaccccccc9cccccccaccccccc
    RO CH_ALIGNER_2INPUT_ALL status 0x2
    RO CH_ALIGNER_3INPUT_ALL select 0x20
    RO CH_ALIGNER_3INPUT_ALL snapshot 0xacccccccaccccccc9cccccccaccccccc
    RO CH_ALIGNER_3INPUT_ALL status 0x2
    RO CH_ALIGNER_4INPUT_ALL select 0x20
    RO CH_ALIGNER_4INPUT_ALL snapshot 0xacccccccaccccccc9cccccccaccccccc
    RO CH_ALIGNER_4INPUT_ALL status 0x2
    RO CH_ALIGNER_5INPUT_ALL select 0x20
    RO CH_ALIGNER_5INPUT_ALL snapshot 0xacccccccaccccccc9cccccccaccccccc
    RO CH_ALIGNER_5INPUT_ALL status 0x2
    RO CH_ALIGNER_6INPUT_ALL select 0x20
    RO CH_ALIGNER_6INPUT_ALL snapshot 0xacccccccaccccccc9cccccccaccccccc
    RO CH_ALIGNER_6INPUT_ALL status 0x2
    RO CH_ALIGNER_7INPUT_ALL select 0x20
    RO CH_ALIGNER_7INPUT_ALL snapshot 0xacccccccaccccccc9cccccccaccccccc
    RO CH_ALIGNER_7INPUT_ALL status 0x2
    RO CH_ALIGNER_8INPUT_ALL select 0x20
    RO CH_ALIGNER_8INPUT_ALL snapshot 0xacccccccaccccccc9cccccccaccccccc
    RO CH_ALIGNER_8INPUT_ALL status 0x2
    RO CH_ALIGNER_9INPUT_ALL select 0x20
    RO CH_ALIGNER_9INPUT_ALL snapshot 0xacccccccaccccccc9cccccccaccccccc
    RO CH_ALIGNER_9INPUT_ALL status 0x2
    ```

  - For the emulator to be aligned:
    - Make sure that the _last_ words of the snapshot are: `9cccccccaccccccc` (7 c's!).
    - `select` must be `0x20`.
    - We want to see the snapshot at ~ the same position. It does not have to be exactly the same.
      A leftward shift of less than 32 bits is OK.
      A rightward shift is not, because then the ASIC will not be able to align (it has to see the complete `0x9cccccccaccccccc` pattern).
    - The `select` register in the ASIC should be in the interval [select_emulator, select_emulator+31bits], e.g. [0x20,0x3f].

  - Sending PRBS and enabling check in ASIC:

    In 32-bit PRBS checking mode, `prbs_chk_err_cnt` should not increment, while `hdr_mm_cntr` and `orbsyn_hdr_err_cnt` will increment.  
    `hdr_mm_cntr` will increment 3563 times faster than `orbsyn_hdr_err_cnt` increments.

    The counters can be set back to zero by writing a `1` to `rw_ecc_err_clr`.
    `hdr_mm_cntr` is NOT reset by `rw_ecc_err_clr`.  Instead, `hdr_mm_cntr` is reset by link_reset_ROCT. It can also be reset by either the RESET_B or SOFT_RESET_B pins or by the ChipSync fast command.
    ChipSync fast command has the same effect as the SOFT_RESET_B pin.

    ```
    # configure to check PRBS (also resets counters)
    python testing/i2c.py --yaml configs/prbs.yaml --write
    # to send PRBS (32 bit)
    python testing/eRx.py --tv --dtype PRBS
    # read prbs_chk_err_cnt
    python testing/i2c.py --name *prbs_chk_err_cnt,*raw_error_prbs_chk_err
    # (before writing the prbs configs, I would see prbs_chk_err_cnt 0xff - maxed out - then went back to 0)
    ```
    
    One can do a phase scan by reading `prbs_chk_err_cnt` while changing `phaseSelect` in `trackMode 0`.
    ```
    python testing/eRx.py --prbs --sleep 1
    ```
  
- IO alignment:
  - Make sure that the algorithm is threshold and that the values of threshold are maximum, for BOTH ASIC and emulator:
    ```
    # algo_select should be 0
    python testing/i2c.py --name MFC_ALGORITHM_SEL_DENSITY_algo_select --i2c ASIC,emulator
    # threshold values should be 0x3fffff
    python testing/i2c.py --name ALGO_threshold_val_[0-47] --i2c ASIC,emulator
    ```
  - Make sure that IO is inverted `--invertIO` by default.
  - Reset IO (and counters) with:
    ```
    python testing/align_on_tester.py --step configure-IO --invertIO
    ```
    Is a good idea to reset IO before checking that is aligned (and many bit transitions are sent).

  - An example of IO aligned:
    ```
    INFO:utils:from-IO link0: bit_tr 0, delay ready 1, error counter 0, bit_counter 36723529
    INFO:utils:from-IO link1: bit_tr 0, delay ready 1, error counter 0, bit_counter 36723522
    INFO:utils:from-IO link2: bit_tr 0, delay ready 1, error counter 0, bit_counter 36723522
    INFO:utils:from-IO link3: bit_tr 0, delay ready 1, error counter 0, bit_counter 36723531
    INFO:utils:from-IO link4: bit_tr 0, delay ready 1, error counter 0, bit_counter 36723535
    INFO:utils:from-IO link5: bit_tr 0, delay ready 1, error counter 0, bit_counter 36723522
    INFO:utils:from-IO link6: bit_tr 0, delay ready 1, error counter 0, bit_counter 36723522
    INFO:utils:from-IO link7: bit_tr 0, delay ready 1, error counter 0, bit_counter 36723522
    INFO:utils:from-IO link8: bit_tr 0, delay ready 1, error counter 0, bit_counter 36723522
    INFO:utils:from-IO link9: bit_tr 0, delay ready 1, error counter 0, bit_counter 36723522
    INFO:utils:from-IO link10: bit_tr 0, delay ready 1, error counter 0, bit_counter 36723535
    INFO:utils:from-IO link11: bit_tr 0, delay ready 1, error counter 0, bit_counter 36723522
    INFO:utils:from-IO link12: bit_tr 0, delay ready 1, error counter 0, bit_counter 36723538
    INFO:align:step:check-IO:from-IO aligned
    ```
  - Sometimes `delay_ready` can be 1 but the link is still waiting for bit transitions (bit_tr=1) and bit counter is 0. In that case is possible that link is not aligned.
    Reset IO, send zero-data with max threshold and TS algo and check again.

- Link capture alignment:
  - If link capture is not aligned:
    - Check that all elinks are word-aligned in ASIC and emulator:
      ```
      python testing/i2c.py --yaml configs/align_read.yaml --i2c ASIC,emulator
      ```
    - You should be able to repeat the procedure of setting `ALIGNER_orbsyn_cnt_load_val,ALIGNER_orbsyn_cnt_snapshot`, sending link reset-ROCT and reading back alignment registers.

  - If you see bit errors in the captured data:
    - Try increasing the drive strength of the eTx and capturing again:
      ```
      python testing/i2c.py --name ETX_ch_*_drive_strength --value 7
      python testing/i2c.py --name  ETX_ch_*_pre_emphasis_strength --value 7

      python testing/eTx.py --capture --lc lc-ASIC --mode linkreset_ECONt --capture --csv
      ```
  - To manually align:
    - Check the output saved in the `check-lcASIC` step: lc-ASIC-alignoutput_debug.csv:
      ```
      f9225922,f9225922,f9225922,f9225922,f9225922,f9225922,f9225922,f9225922,f9225922,f9225922,f9225922,f9225922,f9225922
      0922f922,0922f922,0922f922,0922f922,0922f922,0922f922,0922f922,0922f922,0922f922,0922f922,0922f922,0922f922,0922f922
      ```
    - Manually override the alignment (and modify the snippet with a different delay if needed) with:
      ```
      # read the current align position
      python testing/align_on_tester.py --step manual-lcASIC
      # change the align position (+ or - 16 bits)
      python testing/align_on_tester.py --step manual-lcASIC --alignpos 16
      ```
    - Then check again:
      ```
      python testing/eTx.py --capture --lc lc-ASIC --mode linkreset_ECONt --capture --csv
      ```
      You should have
      ```
      f922f922,f922f922,f922f922,f922f922,f922f922,f922f922,f922f922,f922f922,f922f922,f922f922,f922f922,f922f922,f922f922
      09220922,09220922,09220922,09220922,09220922,09220922,09220922,09220922,09220922,09220922,09220922,09220922,09220922
      ```
