ECON-SW
=======

## Pre-requisites:
- Libraries to compile software:
```bash
sudo yum -y install epel-release
yum install epel-release
yum update
yum install cmake zeromq zeromq-devel cppzmq-devel libyaml libyaml-devel yaml-cpp yaml-cpp-devel boost boost-devel python3 python3-devel autoconf-archive pugixml pugixml-devel
pip3 install pyzmq pyyaml smbus2 nested_dict --user
```
 
- uHal: Visti https://gitlab.cern.ch/hgcal-daq-sw/ipbus-software
```bash
sudo yum install boost boost-devel
sudo yum -y install epel-release
sudo yum install pugixml-devel pugixml
git clone https://gitlab.cern.ch/asteen/ipbus-software.git
cd ipbus-software
git checkout asteen/UIO-hgcal-dev #should be useless since this should be the default branch of this repo
make -j2 Set=uhal
make install -j2 Set=uhal
```

## Install

### Basic installation of econt-sw on Zynq Trenz module:
```bash
# go to main directory
cd econt-sw/
source env.sh
mkdir build
cd build
cmake ../
make install
cd ../
```

## Re-load new firmware

In HGCAL-dev board:
```
# go to little-dt directory
cd /home/HGCAL_dev/src/mylittledt/

# load new firmware, e.g. econ-t-IO-Aug12 and set permissions
sudo ./load.sh ~/firmware/econ-t-IO-Aug12 && sudo chmod a+rw /dev/uio* /dev/i2c-*
```

## Testing
```
# run server for uhal
./bin/zmq-server -I 6677 -f address_table/connection.xml

# run server for i2c (on testing board - zynq - but for now zynq localhost):
cd zmq_i2c/
python3 ./zmq_server.py

# run client (on remote PC - but for now zynq localhost):
python3 ./zmq_align.py
```


```
python3 ./zmq_server.py
./bin/zmq-client -P 6678
./bin/zmq-server -I 6677 -f address_table/connection.xml
python3 zmq_align.py 
```

To debug uHal:
```
./bin/zmq-server -I 6677 -f address_table/connection.xml -L 6
```

