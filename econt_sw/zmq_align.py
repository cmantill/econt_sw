from time import sleep

import zmq_controller as zmqctrl

# IP address of the zynq on the econ-testing board (localhost for the moment)
remoteIP = "localhost"

# port of the zynq waiting for daq (? fc/link) commands
daqPort = "6677"

# port of the zynq waiting for I2C config and commands (initialize/configure)
i2cPort = "5555"

# port for data pulling
pullerPort = "6678"

daq_socket = zmqctrl.daqController(remoteIP, daqPort, "configs/init.yaml")
cli_socket = zmqctrl.daqController("localhost",pullerPort, "configs/init.yaml")
i2c_socket = zmqctrl.i2cController(remoteIP, i2cPort, "configs/init.yaml")

# client socket
cli_socket.yamlConfig['global']['output_directory'] = "/home/HGCAL_dev/src/econt_sw/econt_sw/output/"
cli_socket.yamlConfig['global']['serverIP'] = daq_socket.ip
cli_socket.yamlConfig['global']['data_push_port'] = '8888'
cli_socket.yamlConfig['daq']['delay_scan_port'] = '6678'
#cli_socket.configure()

# i2c 
i2c_socket.initialize()

# daq
daq_socket.configure()

#cli_socket.start()

#daq_socket.delay_scan()

daq_socket.start()

# send i2c prbs
i2c_socket.initialize("zmq_i2c/configs/prbs.yaml")

daq_socket.prbs()

#cli_socket.stop()

#i2c_socket.read_config("configs/init.yaml")
#i2c_socket.read_config("zmq_i2c/configs/read_align.yaml")
i2c_socket.read_config("zmq_i2c/configs/read_prbs.yaml")
#print( yaml.dump(i2csocket.read_config("zmq_i2c/configs/read_align.yaml")) )

