import argparse
import zmq_controller as zmqctrl

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Align links')
    args = parser.parse_args()

    # IP address of the zynq on the econ-testing board
    remoteIP = "localhost"

    # port of the zynq waiting for I2C config and commands
    i2cPort = "5555"
    i2cPortASIC = "5554"

    #for i in range(12):
    i = 6
    #i = 15
    i2c_socket_asic = zmqctrl.i2cController(remoteIP, i2cPortASIC, "configs/align.yaml")
    i2c_socket_asic.yamlConfig['ECON-T']['RW']['ALIGNER_ALL']['registers']['orbsyn_cnt_snapshot']['value'] = i
    i2c_socket_asic.yamlConfig['ECON-T']['RW']['ALIGNER_ALL']['registers']['match_pattern_val']['value'] = 0x9cccccccaccccccc
    #i2c_socket_asic.yamlConfig['ECON-T']['RW']['ALIGNER_ALL']['registers']['match_pattern_val']['value'] = 0xabcd1234accccccc
    i2c_socket_asic.configure()

    i2c_socket = zmqctrl.i2cController(remoteIP, i2cPort, "configs/align.yaml")
    #i2c_socket.yamlConfig['ECON-T']['RW']['ALIGNER_ALL']['registers']['orbsyn_cnt_snapshot']['value'] = i
    i2c_socket.configure()

    import os
    os.system('python testing/align_on_tester.py')
    
    i2c_socket_asic.read_config("configs/align.yaml","read")
