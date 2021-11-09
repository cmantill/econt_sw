from gevent.pywsgi import WSGIServer
from geventwebsocket import WebSocketError
from geventwebsocket.handler import WebSocketHandler
from bottle import request, Bottle, abort, template
app = Bottle()

import time, os
from subprocess import PIPE, Popen
import threading
import socket

hc_name = socket.gethostname()
hc_ip = socket.gethostbyname(hc_name)
lock = threading.Lock()
wsocks = {}
procs = {}

# environment for daq server
env = os.environ.copy()
env["PATH"] = '/opt/cactus/bin:' + env["PATH"]
env["LD_LIBRARY_PATH"]='/opt/cactus/lib:./lib:' + env['LD_LIBRARY_PATH']
env["UHAL_ENABLE_IPBUS_MMAP"]='1'

# commands to execute on server
cmds = {
    'sc':      ['python3', '-u', 'zmq_server.py'], 
    'fc':      ['./bin/zmq-server']
}

cwds = {
    'sc':      './zmq_i2c',
    'fc':      './' 
}

@app.route('/')
def html():
    return template('website', ip=hc_ip, name=hc_name)

@app.route('/websocket')
def handle_socket():
    wsock = request.environ.get('wsgi.websocket')
    if not wsock: abort(400, 'Expected WebSocket request.')
    client_ip = request.environ.get('REMOTE_ADDR')
    wsocks[client_ip] = wsock
    print('WebSocket on {} established.'.format(client_ip))
    for name in procs.keys(): wsock.send('STATE++{}:UP'.format(name))  # initial state

    while True:
        try:
            msg = wsock.receive()
            if msg in procs and procs[msg].poll() is None:  # kill proc, proc running
                procs[msg].terminate()
            elif msg in cmds:   # spawn proc, proc not running
                procs[msg] = Popen(cmds[msg], cwd=cwds[msg], stdout=PIPE, universal_newlines=True, env=env)
                threading.Thread(target=run, args=(msg, procs[msg])).start()
        except WebSocketError:  # close wsock
            wsocks.pop(client_ip)
            break
    print('WebSocket on {} closed.'.format(client_ip)) 

def run(name, proc):
    broadcast('STATE++{}:UP'.format(name))
    for line in iter(proc.stdout.readline, ""):
        broadcast('DATA++{}: '.format(name) + line)
    broadcast('STATE++{}:DOWN'.format(name))
    del procs[name]
    print('Process {} terminated.'.format(name))

def broadcast(msg):
    lock.acquire()
    for _, wsock in wsocks.items():
        wsock.send(msg)
    lock.release()

server = WSGIServer(("0.0.0.0", 8080), app, handler_class=WebSocketHandler)
server.serve_forever()
