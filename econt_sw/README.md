ECON-SW
=======

## Getting started:
- *Libraries to compile software*:
    ```bash
    sudo yum -y install epel-release
    yum install epel-release
    yum update
    yum install cmake zeromq zeromq-devel cppzmq-devel libyaml libyaml-devel yaml-cpp yaml-cpp-devel boost boost-devel python3 python3-devel autoconf-archive pugixml pugixml-devel
    pip3 install pyzmq pyyaml smbus2 nested_dict --user
    ```

- *Clone repository*:
    ```bash
    # clone repository in `src/` folder or other working directory:
    git clone --recursive git@github.com:cmantill/econt_sw.git
    # to update submodules
    cd econt_sw/
    git submodule --init --recursive
    ```

- *uHal*: Visit https://gitlab.cern.ch/hgcal-daq-sw/ipbus-software
    ```bash
    # go into econt_sw directory
    cd econt_sw/

    # install libraries
    sudo yum install boost boost-devel
    sudo yum -y install epel-release
    sudo yum install pugixml-devel pugixml

    # clone ipbus-software
    git clone ssh://git@gitlab.cern.ch:7999/hgcal-daq-sw/ipbus-software.git
    cd ipbus-software/
    git checkout asteen/UIO-hgcal-dev 

    # compile uHal
    make -j2 Set=uhal
    make install -j2 Set=uhal
    ```
## Install:

- **Basic installation of econt-sw on Zynq Trenz module**:
    ```bash
    # go to main directory in econt-sw
    cd econt-sw/econt-sw/

    # source libraries
    source env.sh

    # compile 
    mkdir build
    cd build
    cmake ../
    make install
    cd ../
    ```

- **To re-load new firmware**:

    ```bash
    # go to mylittledt directory
    cd ${MYLITTLEDT}
    cd /home/HGCAL_dev/src/mylittledt/

    # load firmware and set permissions
    sudo ./load.sh ${FIRMWARE_FOLDER}   && sudo chmod a+rw /dev/uio* /dev/i2c-*
    ```

    In HGCAL_dev board:
    ```
    ${MYLITTLEDT} = /home/HGCAL_dev/src/mylittledt/
    ${FIRMWARE_FOLDER} = econ-t-IO-Aug12
    ```
    
    In emulator-to-emulator setup:
    ```
    ${MYLITTLEDT} =  /home/HGCAL_dev/mylittledt/
    ${FIRMWARE_FOLDER} ASIC: `~/firmware/econ-t-emu-solo-Nov12/
    ${FIRMWARE_FOLDER} TESTER: `~/firmware/econ-t-tester-Nov12/
    ```

    To check the version of the firmware:
    ```
    # check which version of the firmware was loaded
    cat /sys/firmware/devicetree/base/fpga-full/firmware-name

    # find out the specific git commit on which the firmware was built
    cat /sys/firmware/devicetree/base/fpga-full/git-desc
    cat /sys/firmware/devicetree/base/fpga-full/git-sha    
    ```

- **When loading new firmware**:
    Need to link `address_table` directory. Default `fw_block_addresses.xml` files are available in the `econt_sw/econt_sw/address_table_reference_*/` directories for comparison.
    ```
    sudo ln -s /opt/hexactrl/uHAL_xml address_table
    ```    

## Testing:

There are 4 components in the testing, either local or remote:

| Remote              | ZYNQ                                 |
| ------------------- | ------------------------------------ |
| Testing script      | Executable (zmq-server)              |
| Client (zmq-client) | Data acqusition (daq and analysis)   |
|                     | Slow control (i2c)                   |

### Ports:

- The *testing script* is run remotely (this can mean on the board or on a testing desktop).
  - It communicates with the *server* executable with `daqPort` (default = 6677)
  - It communicates with the *client* with `pullerPort` (default = 6678)
  - It communicates with the *i2c* slow control with `i2cPort` (default=5555)
- The *client* is also run remotely.
  - It communicates with the *server* with `pullerPort` (default = 6678)
  - It communicates with the *DAQ* with `data_push_port` (default = 8888)

The `remoteIP` is set to `localhost`. 

This means that when running testing scripts remotely one needs to do port forwarding of: `daqPort` and `data_push_port`.

### ZYNQ ECON-T testers:
```
# econ-ASIC (ASIC with emu-solo firmware)
# to fix the IP address one can change the setup on `/etc/dhcp/dhcpd.conf` on the desktop that manages the dchp server
# see more instructions on hexactrl_setup.md
ssh HGCAL_dev@192.168.1.45
   
# econ-emulator (Emulator with tester firmware) 
ssh HGCAL_dev@192.168.1.46
```

### ZYNQ HGCAL_dev:
```
ssh -p 23 HGCAL_dev@wilsonjc.us
```

### Testing locally:
- i2c server
  ```
  cd zmq_i2c/
  python3 ./zmq_server.py
  ```
- zmq server
  ```
  ./bin/zmq-server -I 6677 -f connection.xml
  # To debug uHal add `-L 6`
  ```
- zmq client
  ```
  ./bin/zmq-client -P 6678
  ```
- testing script
  ```
  python3 testing/zmq_align_links.py 
  ```

### Running on remote desktop:

- On the ZYNQ:
  ```
  # Start a terminal session:
  # Run the i2c server
  cd zmq_i2c/
  python3 ./zmq_server.py
  
  # Start a terminal session:
  # Start the server
  ./bin/zmq-server -I 6677 -f connection.xml
  ```
  
  Alternatively, one can use the webserver:
  ```
  # start the server
  python3 webserver.py
  
  # open a web browser : [http://hc640259:8080/](http://hc640259:8080/) (replace hc640259 by the zynq IP address)
  - Select `zynq` (for zynq board) and then press `Load FPGA` button
  - Click `Start` button of the slow control
  - Click `Start` button of the server
  ```
  
- On the remote desktop:
  ```
  # Log-in to 14WH desktop
  ssh -K hcalpro@cmsnghcal01.fnal.gov

  # Start a terminal session:
  # Then, port forward to ZYNQ, e.g.:
  ssh -L 6678:localhost:6678 -L 8888:localhost:8888 -L 6677:localhost:6677 -L 5555:localhost:5555 -p 23 HGCAL_dev@wilsonjc.us

  # Start a terminal session (on the 14WH desktop):
  # Start the client with `pullerPort`:
  cd cmantill/econt_sw/econt_sw/ # or to working directory with econt_sw
  ./bin/zmq-client -P 6678

  # Start a terminal session (on the 14WH desktop):
  # Run the testing script, e.g.:
  cd scripts/
  python3 align_links.py 
  ```
  
### Running on tester setup:

- On the "ASIC":
  ```
  python debug_tools/setupIOdelay.py
  ```
    
- On the "Emulator":
  ```
  # start server for i2c with emulator
  python3 zmq_server.py --addr 0x21
  
  # start server for i2c with asic
  python3 zmq_server.py --addr 0x20 --server 5554
  
  # start the client
  ./bin/zmq-client -P 6678
  
  # start the server
  ./bin/zmq-server -L 6
  
  # test alignment
  python3 testing/zmq-align_links.py
  ```
  
## Tests:

- Fast control:
  - [ ] Test PLL locking with a range of frequencies
  - [ ] Introduce FC errors
  - [ ] OrbitSync (BCR): resets bunch counter to programmable value. Check misplaced BCR by looking at header errors (if it sees the BC0 pattern w/o BCR it will complain).
  - [ ] LINK_RESET_ROCT: triggers programmable alignment pattern to be sent by HGCROC (elinkOutputs). See whether the ECON-T performs its alignment process in response.
  - [ ] LINK_RESET_ECONT: triggers output alignment pattern to be sent to BE.
  - [ ] ChipSync: same as soft reset but does not reset FC.

- Slow control:

  - [x] Test slow control connection:
  ```
  cd zmq_i2c/
  python3 simple_setup.py
  ```
  - [x] Set a fixed address
  ```
  python testing/uhal-i2c_set_address.py --i2c ASIC --addr 0
  python testing/uhal-i2c_set_address.py --i2c emulator --addr 1
  ```
  - [x] Test a fixed address, read/write from/to every bit of every register in the ASIC (only reads for RO registers)
  ```
  python3 testing/i2c.py --i2c ASIC emulator --addr 0,1 --server 5554,5555 --set-address True
  # this does not start a server so it needs servers
  python3 zmq_server.py --addr 0x20 --server 5554
  python3 zmq_server.py --addr 0x21 --server 5555
  ```
  - [x] Test every possible i2c address for the ASIC
  ```
  for i in {0..15}; do python3 testing/i2c.py --i2c ASIC emulator --addr $i,1 --server 5554,5555 --set-address True; done
  ```
  - [x] Read and write one single i2c register
  ```
  # to read
  python3 testing/i2c_single_register.py --i2c ASIC --addr 0  --server 5554  --rw RW --block ALIGNER_ALL --register orbsyn_cnt_snapshot
  # to write (and read)
  python3 testing/i2c_single_register.py --i2c ASIC --addr 0  --server 5554  --rw RW --block ALIGNER_ALL --register orbsyn_cnt_snapshot --read
  ```

- Reset signals:

  - [x] Send reset and release:
  ```
  # send reset
  python testing/reset_signals.py --i2c ASIC --reset hard

  # release
  python testing/reset_signals.py --i2c ASIC --reset hard --release True
  ```
  - [x] Test hard reset: i2c register gets reset
  ```
  python3 testing/resets.py --i2c ASIC emulator  --server 5554,5555 --reset hard
  ```
  - [x] Test soft reset: i2c register left unchanged
  ```
  python3 testing/resets.py --i2c ASIC emulator  --server 5554,5555 --reset soft
  ```

- Alignment sequence:

  - [ ] Phase alignment.
    - [ ] In *ASIC*.
    - [x] In interposer system: align `to-IO`.
  - [x] *Tester* input phase alignment: align `from-IO`.
  - [x] *ASIC* word alignment: send LINK_RESET_ROCT, check snapshot and `select` i2c ASIC status.
  - [x] *Tester* link_capture-ASIC word alignment: send LINK-RESET-ECONT.
  - [x] *Tester* link_capture-ASIC and link_capture-Emulator relative alignment: check relative alignment using `fifo_latency`.

  In python uhal (on tester):
  ```
  # if i2c servers running in different windows
  # python3 zmq_server.py --addr 0x20 --server 5554 # (ASIC)
  # python3 zmq_server.py --addr 0x21 --server 5555 # (emulator)
  python3 testing/align_links.py

  # to run the i2c servers  in the same script
  python3 testing/align_links.py --start-server
  ```

  1. On Tester:
     Execute until: `IO blocks configured. Sending PRBS. Press key to continue...`
  2. On ASIC:
     ```
     python2 testing/uhal-align_on_ASIC.py
     ```
     - Execute until: `IO blocks configured. Waiting for bit transitions. Press key to continue...`
     - Press key.
     - Execute until: `Link capture and counters checked. Waiting for link reset roct. Press key to continue...`
  3. On Tester: Press key
     - Execute until: `Sent link reset ROCT. Press key to continue...`

  Alignment on ECON-T:
  ```
  # first align IO blocks
  python3 testing/align_links.py --start-server --steps tester-phase
  # then, scan values of delay,orbsyn_snap,orbsyn_value
  python3 testing/find_orb.py --start-server --delay 0 --snap 0 0 --val 0 0  
  ```

- Alignment tests:
  - [ ] Test different alignment patterns (i2c).
  - [ ] Check that header errors are correctly detected and counted.

- Delay scan:
  - [x] from-IO delay scan on tester
  ```
  python testing/uhal-delayScan.py
  ```

- PRBS15 to ASIC:
  - [ ] Set PRBS15 with headers (28 bit mode).
  - [ ] Set PRBS15 without headers (32 bit mode).
  - [ ] Crude delay scan in ASIC using PRBS error checking.

- Data path tests:
  - [x] Basic DAQ with repeater algorithm and counter dataset in TC:
  ```
  python3 testing/eventDAQ.py --idir  configs/test_vectors/counterPatternInTC/RPT/ --start-server
  # if need to capture with l1a
  python3 testing/eventDAQ.py --idir  configs/test_vectors/counterPatternInTC/RPT/ --start-server --capture l1a
  ```
  The output of the two link captures will be saved in `configs/test_vectors/counterPatternInTC/`.
  - [x] MUX
  ```
  for i in {1..47..1}
   do
    python3 testing/eventDAQ.py --idir  configs/test_vectors/counterPatternInTC_by2/RPT_MUX_${i}/ --start-server
   done
  ```
  - [x] Calibration
  ```
  ```
  - [x] DropLSB
  ```
  configs/test_vectors/counterPatternInTC/
  ```
  - Algorithms:
    - [x] Threshold Sum
    - [x] STC
    - [ ] BC
    - [ ] AE
  - Formatter/buffer (TS):
    - [ ] Vary buffer thresholds
    - [ ] Test T1 truncation
    - [ ] Test T2/T3 truncation
    - [ ] Fill the buffer
  - Vary eTx enabled

- Error handling logic:
  - [ ] readout of errors
  - [ ] masking of errors
  - [ ] clearing of errors

- ERX:
  - [ ] Test inversion
  - [ ] Test enable

- ETX:
  - [ ] Test inversion
  
- SEU detection: