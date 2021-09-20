import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start i2c server')
    parser.add_argument('--server', type=str,
                        default='5555',
                        help='server for i2c (5555 for ASIC, 5554 for Emulator')
    args = parser.parse_args()

    import zmq_controller as zmqctrl

    # i2c server
    i2c_port = args.server

    # default po
    i2c_socket = zmqctrl.i2cController("localhost", i2c_port)

    # initialize
    i2c_socket.initialize()

    # read
    i2c_read = i2c_socket.read_and_compare()
    print(i2c_read)
