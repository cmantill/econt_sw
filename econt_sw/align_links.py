from time import sleep

import zmq_controller as zmqctrl

# IP address of the zynq on the econ-testing board (localhost for the moment)
remoteIP = "localhost"

# port of the zynq waiting for daq (? fc/link) commands
daqPort = "6677"

# port of the zynq waiting for I2C config and commands (initialize/configure)
i2cPort = "5555"

# initialize controllers
daq_socket = zmqctrl.daqController(remoteIP, daqPort, "configs/init.yaml")
i2c_socket = zmqctrl.i2cController(remoteIP, i2cPort, "configs/init.yaml")

# i2c 
i2c_socket.initialize()

# daq
daq_socket.configure()
daq_socket.start()

# print i2c
i2c_socket.read_config("zmq_i2c/configs/read_align.yaml")
