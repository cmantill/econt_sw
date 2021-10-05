import argparse
import os
import zmq_controller as zmqctrl

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Align links')
    args = parser.parse_args()

    # IP address of the zynq on the econ-testing board
    remoteIP = "localhost"

    # port of the zynq waiting for I2C config and commands
    i2cPort = "5555"
    i2cPortASIC = "5554"

    # configure i2c for alignment
    orbsyn_cnt_snapshot = 7
    match_pattern_val = 0x9cccccccaccccccc
    i2c_socket_asic = zmqctrl.i2cController(remoteIP, i2cPortASIC, "configs/align.yaml")
    i2c_socket_asic.yamlConfig['ECON-T']['RW']['ALIGNER_ALL']['registers']['orbsyn_cnt_snapshot']['value'] = orbsyn_cnt_snapshot
    i2c_socket_asic.yamlConfig['ECON-T']['RW']['ALIGNER_ALL']['registers']['match_pattern_val']['value'] = 0x9cccccccaccccccc
    i2c_socket_asic.configure()

    i2c_socket = zmqctrl.i2cController(remoteIP, i2cPort, "configs/align.yaml")
    i2c_socket.yamlConfig['ECON-T']['RW']['ALIGNER_ALL']['registers']['orbsyn_cnt_snapshot']['value'] = orbsyn_cnt_snapshot
    i2c_socket.yamlConfig['ECON-T']['RW']['ALIGNER_ALL']['registers']['match_pattern_val']['value'] = 0x9cccccccaccccccc
    i2c_socket.configure()

    # read back i2c 
    read_asic = i2c_socket_asic.read_config("configs/align.yaml")
    print('TX sync word ASIC ',hex(read_asic['RW']['FMTBUF_ALL']['tx_sync_word']))

    read_emulator = i2c_socket.read_config("configs/align.yaml")
    print('TX sync word emulator', hex(read_emulator['RW']['FMTBUF_ALL']['tx_sync_word']))

    # phase alignment for IO
    os.system('python testing/uhal-align_on_tester.py --step tester-phase')
    os.system('python testing/uhal-align_on_tester.py --step asic-word')

    # read i2c registers (select and status)
    read_asic = i2c_socket_asic.read_config("configs/align.yaml","read")
    for i in range(12):
        print('Status link %i'%i,hex(read_asic['RO']['CH_ALIGNER_%iINPUT_ALL'%i]['status']))
        print('Snapshot link %i'%i,hex(read_asic['RO']['CH_ALIGNER_%iINPUT_ALL'%i]['snapshot']))

    # relative alignment for IO
    os.system('python testing/uhal-align_on_tester.py --step asic-tester')




