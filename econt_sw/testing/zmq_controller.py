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
        self.yamlConfig = None
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
        merge(self.yamlConfig,config)

    def configure(self,fname="",yamlNode=None):
        print('configure w. ',yamlNode)
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
    def __init__(self,ip,port,fname=None):
        super(i2cController, self).__init__(ip,port,fname)
        
    def initialize(self,fname=None):
        self.socket.send_string("initialize")
        rep = self.socket.recv_string()
        if rep.lower().find("ready")<0:
            print(rep)
            return
    
    def read_and_compare(self):
        self.socket.send_string("compare")
        rep = self.socket.recv_string()
        if rep.lower().find("ready")<0:
            yamlread = yaml.safe_load( self.socket.recv_string() )
            print('yaml read ',yamlread) 
            return

    def read_config(self,fname=None,key=None):
        # print('read config ',fname)
        self.socket.send_string("read")
        rep = self.socket.recv_string()
        if fname:
            with open(fname) as fin:
                config = yaml.safe_load(fin)
            if key is not None:
                config_dict = yaml.dump(config[key])
            else:
                config_dict = yaml.dump(config)
            print('config ',config)
            self.socket.send_string( config_dict )
        else:
            print('no fname')
            self.socket.send_string( "" )
        yamlread = yaml.safe_load( self.socket.recv_string() )
        # print('yaml read ',yamlread)
        print('i2cController::read back')
        for access,accessDict in yamlread.items():
            for block,blockDict in accessDict.items():
                for param, paramDict in blockDict.items():
                    print(access,block, param, hex(yamlread[access][block][param]))
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

    def delay_scan(self):
        # only for daq server to run a delay scan
        print('delay scan')
        rep=""
        while rep.lower().find("delay_scan_done")<0: 
            self.socket.send_string("delayscan")
            rep = self.socket.recv_string()
        print(rep)

    def prbs_test(self):
        print('prbs test')
        rep=""
        while rep.lower().find("prbs_test_done")<0:
            self.socket.send_string("prbstest")
            rep = self.socket.recv_string()
        print(rep)

    def i2c_scan(self, fname=None, yamlNode=None):
        print('i2c address scan')
        self.socket.send_string("i2cscan")
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
        print(rep)
