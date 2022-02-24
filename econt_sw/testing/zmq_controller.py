import zmq
import yaml
from time import sleep
from nested_dict import nested_dict
import logging
import sys

def _init_logger():
    logger = logging.getLogger('zmqcontroller')
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(created)f:%(levelname)s:%(name)s:%(module)s:%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def merge(a, b, path=None):
    "merges b into a"
    if path is None: path = []
    if a is None: return b
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a

class zmqController:
    def __init__(self,ip,port,fname="configs/init.yaml"):
        context = zmq.Context()
        self.ip=ip
        self.port=port
        self.socket = context.socket( zmq.REQ )
        self.socket.connect("tcp://"+str(ip)+":"+str(port))
        self.yamlConfig = None
        self.logger = _init_logger()
        if fname:
            with open(fname) as fin:
                self.yamlConfig=yaml.safe_load(fin)

    def reset(self):
        self.socket.close()
        context = zmq.Context()
        self.socket = context.socket( zmq.REQ )
        self.socket.connect("tcp://"+str(self.ip)+":"+str(self.port))

    def update_yamlConfig(self,fname="",yamlNode=None):
        if yamlNode:
            config=yamlNode
        elif fname :
            with open(fname) as fin:
                config=yaml.safe_load(fin)
        else:
            print("ERROR in %s"%(__name__))
        self.yamlConfig = merge(self.yamlConfig,config)

    def configure(self,fname="",yamlNode=None):
        self.socket.send_string("configure")
        rep = self.socket.recv_string()
        if rep.lower().find("ready")<0:
            return
        if yamlNode:
            config=yamlNode
        elif fname :
            with open(fname) as fin:
                config=yaml.safe_load(fin)
        else:
            config = self.yamlConfig
        self.socket.send_string(yaml.dump(config))
        rep = self.socket.recv_string()


class i2cController(zmqController):    
    def __init__(self,ip,port,fname=None):
        super(i2cController, self).__init__(ip,port,fname)
        
    def initialize(self,fname=None):
        self.socket.send_string("initialize")
        rep = self.socket.recv_string()
        if rep.lower().find("ready")<0:
            return
        else:
            return None
    
    def read_and_compare(self,access="RW"):
        if access=="RW":
            self.socket.send_string("compare-rw")
        else:
            self.socket.send_string("compare-ro")
        rep = self.socket.recv_string()
        return rep

    def read_config(self,fname=None,key=None,yamlNode=None):
        self.socket.send_string("read")
        rep = self.socket.recv_string()
        if fname:
            with open(fname) as fin:
                config = yaml.safe_load(fin)
            if key is not None:
                config_dict = yaml.dump(config[key])
            else:
                config_dict = yaml.dump(config)
            self.socket.send_string( config_dict )
        elif yamlNode:
            config_dict = yamlNode
            self.socket.send_string( yaml.dump(config_dict) )
        else:
            self.socket.send_string( "" )
        recv = self.socket.recv_string()
        yamlread = yaml.safe_load( recv ) 
        return( yamlread )

class daqController(zmqController):
    def start(self):
        rep=""
        while rep.lower().find("running")<0: 
            self.socket.send_string("start")
            rep = self.socket.recv_string()
            print(rep)

    def stop(self):
        self.socket.send_string("stop")
        rep = self.socket.recv_string()
        print(rep)

    def align(self):
        print('align')
        rep=""
        while rep.lower().find("align_done")<0:
            self.socket.send_string("align")
            rep = self.socket.recv_string()
            print(rep)
        print(rep)
