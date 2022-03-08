import zmq
import yaml
from time import sleep
from nested_dict import nested_dict
from typing import cast, Dict, Any
import logging
import sys
import numpy as np

def _init_logger():
    logger = logging.getLogger('zmqcontroller')
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

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
    def __init__(self,ip,port,fname="configs/init.yaml",timeout=10000):
        context = zmq.Context()
        self.ip=ip
        self.port=port
        self.socket = context.socket( zmq.REQ )
        self.socket.connect("tcp://"+str(ip)+":"+str(port))
        self.yamlConfig = None
#        self.logger = _init_logger()
        self.logger = logging
        self.socket.RCVTIMEO = timeout
        self.socket.SNDTIMEO = timeout
        self.socket.LINGER = timeout
        if fname:
            with open(fname) as fin:
                self.yamlConfig=yaml.safe_load(fin)

    def reset(self):
        self.socket.close()
        context = zmq.Context()
        self.socket = context.socket( zmq.REQ )
        self.socket.connect("tcp://"+str(self.ip)+":"+str(self.port))

    def close(self):
        self.socket.close(0)

    def update_yamlConfig(self,fname="",yamlNode=None):
        if yamlNode:
            config=yamlNode
        elif fname :
            with open(fname) as fin:
                config=yaml.safe_load(fin)
        else:
            print("ERROR in %s"%(__name__))
        self.yamlConfig = merge(self.yamlConfig,config)

    def setTimeout(self, timeout=1000):
        self.socket.RCVTIMEO = timeout

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
        try:
            rep = self.socket.recv_string()
        except zmq.error.Again:
            self.logger.error('Timeout, check that I2C server is running')
            exit(1)
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
    def recv_array(self, flags=0, copy=True, track=False):
        """recv a numpy array"""
        md = cast(Dict[str, Any], self.socket.recv_json(flags=flags))
        msg = self.socket.recv(flags=flags, copy=copy, track=track)
        A = np.frombuffer(msg, dtype=md["dtype"])
        return A.reshape(md["shape"])
    
    def start_daq(self):
        rep=""
        while rep.lower().find("ready")<0: 
            self.socket.send_string("startdaq")
            rep = self.socket.recv_string()

    def stop_daq(self,timestamp="Mar17"):
        """Latch counters and returns 4 rows of data 28-32 by default"""
        self.socket.send_string(f"stopdaq {timestamp}")
        err_counter = self.socket.recv_string()
        self.logger.info(f'Error counter {err_counter}')
        if int(err_counter)>0:
            self.socket.send_string("getdata")
            ret_array = self.recv_array(copy=False)
            self.logger.info('ASIC array %s', ret_array[:4])
            self.logger.info('emulator array %s', ret_array[4:8])
            self.logger.info('input array %s', ret_array[8:,:-1])
            return ret_array[:4],ret_array[4:8],ret_array[8:,:-1]
        return None

    def getpll(self):
        self.socket.send_string("getpll")
        rep = self.socket.recv_string()
        return rep

    def resetpll(self):
        self.socket.send_string("resetpll")
        rep = self.socket.recv_string()
        return rep

    def set_testVectors(self, arg):
        print(arg)
        self.socket.send_string(f"testvector {arg}")
        rep = self.socket.recv_string()
        return rep
