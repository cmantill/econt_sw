import uhal

if __name__ == "__main__":    
    import zmq_controller as zmqctrl

    # i2c server
    i2cPort = "5555"
    i2c_socket = zmqctrl.i2cController("localhost", i2cPort, "configs/test_i2c_align.yaml")

    # initialize
    i2c_socket.initialize()

    # read
    i2c_read = i2c_socket.read_config()
    print(i2c_read)

