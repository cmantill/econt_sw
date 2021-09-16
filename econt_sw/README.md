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
    git clone git@github.com:cmantill/econt_sw.git
    ```

- *uHal*: Visit https://gitlab.cern.ch/hgcal-daq-sw/ipbus-software
    ```bash
    # go to first directory
    cd econt-sw/

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

    In HGCAL-dev board:
    ```bash
    # go to little-dt directory
    cd /home/HGCAL_dev/src/mylittledt/

    # load new firmware, e.g. econ-t-IO-Aug12 and set permissions
    sudo ./load.sh ~/firmware/econ-t-IO-Aug12 && sudo chmod a+rw /dev/uio* /dev/i2c-*
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
    Need to link `address_table` directory. Default `fw_block_addresses.xml` files are available in the `econt_sw/econt_sw/` directory for comparison.
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
    # econ-tester1 (ASIC with emu-solo firmware)
    # to fix the IP address one can change the setup on `/etc/dhcp/dhcpd.conf` on the desktop that manages the dchp server
    ssh HGCAL_dev@192.168.1.45
   
    # econ-tester2 (Emulator with tester firmware)
    ssh HGCAL_dev@192.168.1.46
```

### ZYNQ HGCAL_dev:
```
    ssh -p 23 HGCAL_dev@wilsonjc.us
```

### Testing locally:
1. Start a terminal session:
```
    # Run the i2c server
    cd zmq_i2c/
    python3 ./zmq_server.py
```
2. Start a terminal session:
```
    # Start the server
    ./bin/zmq-server -I 6677 -f address_table/connection.xml
    # To debug uHal add `-L 6`
```
3. Start a terminal session:
```
    # Start the client
    ./bin/zmq-client -P 6678
```
4. Start a terminal session:
```
    # Run the testing script, e.g.:
    cd scripts/
    python3 align_links.py 
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
  ./bin/zmq-server -I 6677 -f address_table/connection.xml
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
  # Then, port forward to ZYNQ:
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
  python3 testing/align_links.py
  ```
  
  


