import zmq
import yaml
import econ_interface

""" ZMQ-Server: Redirect user request to Board. """
context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")
print('[ZMQ] Server started')

def redirect(fn):
    socket.send_string('READY')
    cfg_str  = socket.recv_string()
    print('redirect ',cfg_str)
    cfg_yaml = yaml.safe_load(cfg_str)
    ans_yaml = fn(cfg_yaml)
    ans_str  = yaml.dump(ans_yaml, default_flow_style=False)
    socket.send_string(ans_str)

try:
    board = econ_interface.econ_interface()

    while True:
        string = socket.recv_string().lower()
        if string == "initialize" or string == "configure":
            if board: redirect(board.configure)
            else: socket.send_string("E: Board not initialized.")

        elif string == "read": redirect(board.read)

except KeyboardInterrupt:
    print('\nClosing server.')
    socket.close()
    context.term()
