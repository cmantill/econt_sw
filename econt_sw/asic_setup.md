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
  * Sets startup registers on ASIC (including those that lock PLL).
  * Sets the phase manually depending on $BOARD.
  * Sets a value of phase of enable.
  * Sets the run bit to 1.
  * Reads the Power-Up-State-Machine status.
     
- Initialize FPGA and do input word alignment:
  ```
  python testing/setup.py input
  ```
  * Configure IO (with `invert` option selected):
  * Resets fast commands, sets input clock to 40MHz, sends bit transitions with 28 bit PRBS (in the test vectors block).
  * Configures ALIGNER for automatic alignment.
  * Loops over possible values of ASIC `snapshot_bx` and sends a link-reset-ROCT until training pattern is found for the ASIC.
  * Loops over possible values of `delay` and sends a link-reset-ROCT until training pattern is found in the correct spot for the emulator.

- Align the output links:
  ```
  python testing/setup.py output
  ```
  * Switch to threshold algorithm.
  * Align IO and switch to manual alignment
  * Align ASIC output link capture.
  * Modify ASIC and emulator latency.
  
- Align the output links using bypass (RPT alignment dataset):
  ```
  python testing/setup.py bypass --align
  ```
  * Configure alignment inputs
  * Configure RPT outputs
  * Set ASIC and emulator latency to align
  
- Compare ASIC and emulator w bypass:
  ```
  python testing/setup.py bypass --compare --idir configs/test_vectors/alignment/BC_10eTx/
  ```
  
## Other functionalities
 ### eRx
  - You can log in hdr mis-match counters (should be estable with good phase alignment), with:
    ```
    python testing/eRx.py --logging -N 1 --sleep 2
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
    
 ### Input
  - To send zero-data:
    ```
    python testing/eRx.py --tv --dtype zeros
    ```
  - With an output produced by elink outputs:
    ```
    python testing/eRx.py --tv --dtype ((PRBS,PRBS32,PRBS28,zeros)
    ```
  - With input test vectors in `idir`:
    ```
    python testing/eRx.py --tv --idir $IDIR
    ``` 
    
  ### Output
  - Check if link capture is aligned
    ```
    python testing/check_block.py --check --block lc-ASIC
    ```
  - Print configuration
    ```
    python testing/check_block.py --check --block lc-ASIC
    ```
  - Read current latency settings for ASIC and emulator
    ```
    python testing/check_block.py -B latency
    ```
  - To check the number of words that agree.
    ```
    python testing/eTx.py --compare --sleep 1 --nlinks 13
    ```  
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
    
  ### IO
  - To perform delay scan:
    ```
    python testing/delay_scan.py --odir $ODIR
    ````
  - To print eye width and registers:
    ```
    python testing/check_block.py --block from-IO
    ```
  - To check alignment:
    ```
    python testing/check_block.py --check -B from-IO
    ````

  ### Inversion
   - Test inverting ERX from IO block and with i2c registers:
     ```
     # configure IO block
     # i2c (change values to 1 to invert)
     python testing/i2c.py --name ERX_ch_*_invert_data --value 0 --quiet
     # check snapshot
     python testing/eRx.py --snapshot
     ```
     
  ### PLL_phase_of_enable_1G28 Scan
   - To scan PLL_phase_of_enable_1G28 while sending zeros and just scan headers (assuming 0 is good Phase that you want to go back to):
     ```
     python testing/eTx.py --scan --good 0 --bx 40 --nwords 100
     ```
  
  ### Fast commands
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
