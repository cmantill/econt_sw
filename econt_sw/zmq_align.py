from time import sleep
import zmq_controller as zmqctrl

# IP address of the zynq on the econ-testing board (localhost for the moment)
remoteIP = "localhost"

# port of the zynq waiting for daq (? fc/link) commands
daqPort = "6000"

# port of the zynq waiting for I2C config and commands (initialize/configure)
i2cPort = "5555"

# port of the client PC (localhost for the moment) waiting for daq config and commands (configure/start/stop)
clientPort = "6001"

daq_socket = zmqctrl.zmqController(remoteIP, daqPort, "configs/init.yaml")
client_socket = zmqctrl.zmqController("localhost", clientPort, "configs/init.yaml")
i2c_socket = zmqctrl.i2cController(remoteIP, i2cPort, "configs/init.yaml")

# i2c configure
i2c_socket.configure()
