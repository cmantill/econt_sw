import argparse
import zmq_controller as zmqctrl

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start i2c server')
    args = parser.parse_args()

    # current path
    import pathlib
    p = pathlib.Path(__file__).parent.resolve()
    print(p)

    # IP address of the zynq on the econ-testing board
    remoteIP = "localhost"
    
    # port of the zynq waiting for daq commands
    daqPort = "6677"

    # port of the zynq waiting for I2C config and commands
    i2cPort = "5555"
    
    # port for data pulling 
    pullerPort = "6678"

    daq_socket = zmqctrl.daqController(remoteIP, daqPort, "configs/align.yaml")
    cli_socket = zmqctrl.daqController("localhost",pullerPort, "configs/align.yaml")
    i2c_socket = zmqctrl.i2cController(remoteIP, i2cPort, "configs/align.yaml")
    
    # initialize i2c
    i2c_socket.initialize("{}/../configs/align.yaml".format(p))

    # client options
    cli_socket.yamlConfig['global']['output_directory'] = "{}/../output/align/".format(p)
    cli_socket.yamlConfig['global']['serverIP'] = daq_socket.ip
    cli_socket.yamlConfig['global']['data_push_port'] = '8888'
    cli_socket.yamlConfig['daq']['delay_scan_port'] = pullerPort

    # configure daq
    daq_socket.configure()
    # align links
    daq_socket.start()

    # read back i2c alignment
    i2c_socket.read_config("configs/align.yaml","read")
    
