from smbus2 import SMBus, i2c_msg

class econ_i2c:
    def __init__(self, busId = 1):
        self._bus = SMBus(busId)
        self._bus.pem = 1

    def read(self, address, register = None, ndata = 1):
        if register != None:
            msg_send = i2c_msg.write(address, [(register >> 8) & 0xff, register & 0xff])
            msg_recv = i2c_msg.read(address, ndata)
            self._bus.i2c_rdwr(msg_send, msg_recv)
        else:
            msg_recv = i2c_msg.read(address, ndata)
            self._bus.i2c_rdwr(msg_recv)
            
        return list(msg_recv)

    def write(self, address, register, data=None):
        send_bytes = [(register >> 8) & 0xff, register & 0xff]
        if(data):
            send_bytes.extend(data)
        msg_send = i2c_msg.write(address, send_bytes)
        self._bus.i2c_rdwr(msg_send)
