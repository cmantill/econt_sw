
## Pre-requisites:

- some libraries:
```bash
sudo yum -y install epel-release
yum install epel-release
yum update
yum install cmake zeromq zeromq-devel cppzmq-devel libyaml libyaml-devel yaml-cpp yaml-cpp-devel boost boost-devel python3 python3-devel autoconf-archive pugixml pugixml-devel
pip3 install pyzmq pyyaml smbus2 nested_dict --user
```

- uhal : visit https://gitlab.cern.ch/hgcal-daq-sw/ipbus-software
```
git clone https://gitlab.cern.ch/asteen/ipbus-software.git
cd ipbus-software
git checkout asteen/UIO-hgcal-dev #should be useless since this should be the default branch of this repo
make -j2 Set=uhal
make install -j2 Set=uhal
```

## Install

### Basic installation of econt-sw on the zynq:
```bash
cd econt-sw
mkdir build
cd build
cmake ../
make install
cd ../
source env.sh
```


## Testing
```
./bin/test -f address_table/connection.xml 
```