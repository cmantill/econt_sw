import pytest
import uhal
import logging 
import sys
import os
import subprocess
import time
import datetime

sys.path.append("..")

from utils.asic_signals import ASICSignals
from utils.fast_command import FastCommands
from utils.io import IOBlock
from utils.link_capture import LinkCapture
from utils.pll_lock_count import PLLLockCount
from utils.stream_compare import StreamCompare
from utils.test_vectors import TestVectors
from utils.uhal_config import *
from i2c import I2C_Client
from PLL_class import pll_freq_setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Possible values for scope are: function, class, module, package or session.
@pytest.fixture(scope="session")
def firmware_name():
    return get_firmware_name()


def get_firmware_name():
    with open(
        "/sys/firmware/devicetree/base/fpga-full/firmware-name"
    ) as firmware_name_file:
        fname = firmware_name_file.read()
    return fname


def firmware_git_desc():
    with open("/sys/firmware/devicetree/base/fpga-full/git-desc", "r") as _file:
        git_desc = _file.read()[:-1]
    return git_desc


def run_git_command(command):
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            return result.stdout.decode("utf-8").strip()
        else:
            return "Error: {}".format(result.stderr.decode("utf-8").strip())
    except FileNotFoundError:
        return "Error: Git command not found. Make sure Git is installed."

@pytest.fixture(scope="session")
def bus_id(firmware_name):
    if "tester" in firmware_name:
        return 1
    else:
        raise ValueError(f"We don't understand the firmware named {firmware_name}")


@pytest.fixture(scope="session")
def blocks(firmware_name):
    if "tester" in firmware_name:
        return names
    else:
        raise ValueError(f"We don't understand the firmware named {firmware_name}")


uhal.setLogLevelTo(uhal.LogLevel.ERROR)
manager = uhal.ConnectionManager(connections_file)
global_uhal_hw = manager.getDevice(dev)


@pytest.fixture(scope="session")
def uhal_hw():
    return global_uhal_hw

# This covers both support_asic and support_emu used in ECOND
@pytest.fixture(scope="session")
def support():
    return ASICSignals()

# this covers both i2c_asic and i2c_emu
def i2c():
    return I2C_Client()

@pytest.fixture(scope="session")
def fc():
    fc = FastCommands()
    fc.configure_fc(self,read=False)
    return fc

@pytest.fixture(scope="session")
def sc():
    return StreamCompare()

#covers lc_input, lc_asic, and lc_emu
@pytest.fixture(scope="session")
def lc():
    return LinkCapture()

@pytest.fixture(scope="session")
def tv():
    return TestVectors()

@pytest.fixture(scope="session")
def tv_bypass():
    return TestVectors('bypass')

##
## Space for aligner fixture
##

@pytest.fixture(scope="session")
def to_IO(firmware_name):
    if "tester" in firmware_name:
        return IOBlock('to')

@pytest.fixture(scope="session")
def from_IO(firmware_name):
    if "tester" in firmware_name:
        return IOBlock('from')
#sets i2c address for both asic and emulator
@pytest.fixture(scope="session")
def i2c_address_setter(support):
    """
    i2c args: "ASIC", "EMU"
    """

    def _set_i2c_address(new_asic_address):
        support.set_i2caddr(i2c, new_asic_address)
       
    return _set_i2c_address

@pytest.fixture(scope="session")
def PLLfreq():
    return pll_freq_setup(shortList=True)

############
# End of basic object construction
# Now move on to setting up test preconditions

@pytest.fixture
def normal_I2C_addresses(i2c_address_setter):
    """
    Set the ASIC I2C address to 0x20 and the emu I2C address to 0x21
    """
    i2c_address_setter('ASIC',0)
    i2c_address_setter('emulator',1)


@pytest.fixture
def hard_reset(support, i2c, from_IO):
    """
    Cycle hard reset and set the run bit to 1
    """
    support.send_reset(reset='hard',i2c='ASIC')

    # after a hard reset, set the run bit to 1, and reset links
    i2c.call(args_name="MISC_run",args_value=1,args_i2c='ASIC')
    i2c.call(args_name="MISC_run",args_value=1,args_i2c='emulator')
    from_IO.reset_links()

    support.send_reset(reset='hard',i2c='emulator')

@pytest.fixture
def out_of_reset(support):
    """
    Take the ASIC and the emu out of reset
    """
    support.out_of_reset('ASIC')
    support.out_of_reset('emulator')

@pytest.fixture
def I2C_both(out_of_reset, normal_I2C_addresses, i2c):
    """
    Set the same I2C run configuration for both the ASIC and the emulator, and
    unset then set the run bits before and afterwards.

    Usually, we should use simultaneous_i2c_write_all instead, and reserve this
    for relatively rare occasions.
    """

    def _I2C_both(args_names=None, args_values=None):
        # First, set both run bits to 0
        i2c.call(args_name="MISC_run",args_value=0,args_i2c='ASIC')
        i2c.call(args_name="MISC_run",args_value=0,args_i2c='emulator')
        # Then do the I2C configuration we want
        i2c.call(args_name=args_names,args_value=args_values,args_i2c='ASIC')
        i2c.call(args_name=args_names,args_value=args_values,args_i2c='emulator')
        # Then set the run bits back to 1
        i2c.call(args_name="MISC_run",args_value=1,args_i2c='ASIC')
        i2c.call(args_name="MISC_run",args_value=1,args_i2c='emulator')

    return _I2C_both



