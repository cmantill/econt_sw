import zmq
import yaml
from time import sleep
from nested_dict import nested_dict

# This acts like the client

def merge(a, b, path=None):
    "merges b into a"
    if path is None: path = []
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
        merge(self.yamlConfig,config)

    def configure(self,fname="",yamlNode=None):
        self.socket.send_string("configure")
        rep = self.socket.recv_string()
        if rep.lower().find("ready")<0:
            print(rep)
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
        #print(rep)


class i2cController(zmqController):    
    def __init__(self,ip,port,fname="configs/init.yaml"):
        super(i2cController, self).__init__(ip,port,fname)
        
    def initialize(self,fname=""):
        # only needed for I2C server
        print(self.ip, self.port)
        self.socket.send_string("initialize")
        rep = self.socket.recv_string()
        if rep.lower().find("ready")<0:
            print(rep)
            return
        if fname :
            with open(fname) as fin:
                config=yaml.safe_load(fin)
        else:
            config = self.yamlConfig
        self.socket.send_string(yaml.dump(config))
        rep = self.socket.recv()
        print(rep)
        # return rep
    
    def read_config(self,yamlNode=None):
        # only for I2C server
        self.socket.send_string("read")
        rep = self.socket.recv_string()
        if yamlNode:
            self.socket.send_string( yaml.dump(yamlNode) )
        else:
            self.socket.send_string( "" )
        yamlread = yaml.safe_load( self.socket.recv_string() )
        return( yamlread )
