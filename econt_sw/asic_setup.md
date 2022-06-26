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
  python testing/setup.py init -b $BOARD
  ```
  -  Some functionalities:
   * Sets startup registers on ASIC (including those that lock PLL).
   * Sets the phase manually depending on $BOARD.
   * Sets a value of phase of enable.
   * Sets the run bit to 1.
   * Reads the Power-Up-State-Machine status.
     
- Initialize FPGA and do input word alignment:
  ```
  python testing/setup.py input
  ```
  - Some functionalities:
  * Configure IO (with `invert` option selected):
  * Resets fast commands, sets input clock to 40MHz, sends bit transitions with 28 bit PRBS (in the test vectors block).
  * Configures ALIGNER for automatic alignment.
  * Loops over possible values of ASIC `snapshot_bx` and sends a link-reset-ROCT until training pattern is found for the ASIC.
  * Loops over possible values of `delay` and sends a link-reset-ROCT until training pattern is found in the correct spot for the emulator.

- Align the output links:
  ```
  python testing/setup.py output
  ```
- Align the output links using bypass (RPT alignment dataset):
  ```
  python testing/setup.py bypass
  ```
  
### More useful
  - You can log in hdr mis-match counters (should be estable with good phase alignment), with:
    ```
    python testing/eRx.py --logging -N 1 --sleep 2
    ```
  - To send zero-data:
    ```
    python testing/eRx.py --tv --dtype zeros
    ```
  - To check alignment:
    ```
    python testing/check_block.py --check --block from-IO
    python testing/check_block.py --check --block lc-ASIC
    python testing/check_block.py --check -B from-IO
    python testing/check_block.py --check -B lc-ASIC
    python testing/check_block.py -B latency
    ```
  - To print eye width and registers:
    ```
    python testing/check_block.py --block from-IO
    ```
  - To check the number of words that agree.
    ```
    python testing/eTx.py --compare --sleep 1 --nlinks 13
    ```
  - With an output produced by elink outputs:
    ```
    python testing/eRx.py --tv --dtype ((PRBS,PRBS32,PRBS28,zeros)
    ```
  - With input test vectors in `idir`:
    ```
    python testing/eRx.py --tv --idir $IDIR
    ```
  - To check `hdr_mm_cntr`:
    ```
    python testing/eRx.py --hdrMM
    ```
  - To manually take a snapshot at a fixed BX:
    ```
    python testing/eRx.py --snapshot --bx 4 
    ```
  - To do PRBS scan:
    ```
    python testing/eRx.py --prbs --sleep 1
    ````

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

## ITA Testing
   - Defaults:
   ```
   python testing/i2c.py --yaml configs/ITA/ITA_defaults.yaml --i2c ASIC,emulator --write --quiet
   ```
