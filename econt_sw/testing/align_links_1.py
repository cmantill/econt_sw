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

    i = 6
    #i = 7
    i2c_socket_asic = zmqctrl.i2cController(remoteIP, i2cPortASIC, "configs/align.yaml")
    i2c_socket_asic.yamlConfig['ECON-T']['RW']['ALIGNER_ALL']['registers']['orbsyn_cnt_snapshot']['value'] = i
    i2c_socket_asic.yamlConfig['ECON-T']['RW']['ALIGNER_ALL']['registers']['match_pattern_val']['value'] = 0x9cccccccaccccccc
    i2c_socket_asic.configure()

    i2c_socket = zmqctrl.i2cController(remoteIP, i2cPort, "configs/align.yaml")
    i2c_socket.yamlConfig['ECON-T']['RW']['ALIGNER_ALL']['registers']['orbsyn_cnt_snapshot']['value'] = i
    i2c_socket.yamlConfig['ECON-T']['RW']['ALIGNER_ALL']['registers']['match_pattern_val']['value'] = 0x9cccccccaccccccc
    i2c_socket.configure()

    import os
    os.system('python testing/align_on_tester_1.py')
    os.system('python testing/align_on_tester_2.py')

    # i2c_socket.read_config("configs/align.yaml","read")
    read_asic = i2c_socket_asic.read_config("configs/align.yaml","read")
    for i in range(12):
        print('Status link %i'%i,hex(read_asic['RO']['CH_ALIGNER_%iINPUT_ALL'%i]['status']))
        print('Snapshot link %i'%i,hex(read_asic['RO']['CH_ALIGNER_%iINPUT_ALL'%i]['snapshot']))

    os.system('python testing/align_on_tester_3.py')
