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

    # numpy
    sudo yum install python-pip
    sudo yum install python-devel
    sudo yum groupinstall 'development tools'
    sudo pip install future
    sudo pip install numpy==1.9

    # clone ipbus-software
    git clone ssh://git@gitlab.cern.ch:7999/hgcal-daq-sw/ipbus-software.git
    cd ipbus-software/
    git checkout asteen/UIO-hgcal-dev 

    # compile uHal
    make -j2 Set=uhal
    make install -j2 Set=uhal
    ```

- *python3 compatible uhal installation*
   If compiling to python3 instead of python2, do not checkout the `asteen/UIO-hgcal-dev` branch, but stick to the default `hgcal-uio` branch from the `hgcal-daq-    sw/ipbus-software.git` repository.  Additionally, the `pybind11` libraries need to be installed:

    ```
    sudo pip3 install pybindll[global]
    ```

    The Makefiles need to be updated in a couple of spots to build the python3 bindings instead of defaulting to python2

    In `config/Makefile.macros`, line 8, change `python` to `python3`
    ```
    -PYTHON ?= python
    +PYTHON ?= python3
    ```
    and in `uhal/Makefile`, lines 22:
    ```
    -       PACKAGES := $(filter-out python, $(PACKAGES))
    +       PACKAGES := $(filter-out python3, $(PACKAGES))
    ```
    and line 57:
    ```
    -PYTHON ?= python
    +PYTHON ?= python3
    ```

    Then, finally, compile:
    ```
    # compile uHal
    sudo make -j2 Set=uhal
    sudo make install -j2 Set=uhal
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

## Firmware:

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
    ${FIRMWARE_FOLDER} ASIC: `~/firmware/econ-t-tester2-Dec3/
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

### ZYNQ ECON-T testers:
To fix the IP address one can change the setup on `/etc/dhcp/dhcpd.conf` on the desktop that manages the dchp server.
See more instructions on hexactrl_setup.md
```
# On 14WH
ssh -K hcalpro@cmsnghcal01.fnal.gov
# econ-board 3
ssh HGCAL_dev@192.168.1.45   
# econ-board 2
ssh HGCAL_dev@192.168.1.48

# Outside
# hgcal-dev (from Jon)
ssh -p 23 HGCAL_dev@wilsonjc.us
```

### Slow control
- We use a zmq_server to start the [econ_interface](https://github.com/cmantill/econt_sw/blob/master/econt_sw/zmq_i2c/econ_interface.py) class.
- To start the server:
  ```
  # start server for i2c with asic
  cd zmq_i2c/
  python3 zmq_server.py --addr ADDRESS --server SERVER
  ```
- To interact with the econ_interface class one can use [testing/i2c.py](https://github.com/cmantill/econt_sw/blob/master/econt_sw/testing/i2c.py). This follows the following structure:
  ```
  for key in server.keys():
      i2c_sockets[key] = i2cController("localhost", str(server[key]))

      # to initialize
      i2c_sockets[key].initialize()
      # to update yaml config
      i2c_sockets[key].update_yamlConfig(yamlNode=new_config)

      # to configure
      i2c_sockets[key].configure()
      # to read values from yaml file and compare
      i2c_read = i2c_sockets[key].read_and_compare()
  
      # to read values
      read_socket = i2c_sockets[key].read_config(yamlNode=new_config)

    # terminate i2c servers
    for key,proc in procs.items():
        proc.terminate()
  ```
  - Examples of using the i2c.py script:
    Add `--quiet` if you do not want printouts
    - With a yaml file
      ```
      # To read the registers in a yaml file
      python3 testing/i2c.py --yaml configs/align.yaml
      ```
    - With specific register:
      ```
      # To read a specific register given access,block,register_name
      python3 testing/i2c.py --i2c ASIC --addr 0 --server 5554  --rw RW --block ALIGNER_ALL --register orbsyn_cnt_snapshot
      
      ```
    - To match the name with [ECON_i2c_dict.json](https://github.com/cmantill/econt_sw/blob/master/econt_sw/zmq_i2c/reg_maps/ECON_I2C_dict.json)
      ```
      # To read all header mis-match counters from ALIGNER block
      python3 testing/i2c.py --name CH_ALIGNER*hdr_mm_cntr
      # or
      python3 testing/i2c.py --name CH_ALIGNER[0-11]_hdr_mm_cntr
      # or
      python3 testing/i2c.py --name CH_ALIGNER[0-2]_hdr_mm_cntr
      ```
    - To list all the matching names in the json file:
      ```
      python3 testing/i2c.py --name CH_ALIGNER* --list
      ```
  - IMPORTANT: To write use all the above options but add `--write`.
- To start default serves for ASIC and emulator see [startServers.sh](https://github.com/cmantill/econt_sw/blob/master/econt_sw/zmq_i2c/startServers.sh).
  
