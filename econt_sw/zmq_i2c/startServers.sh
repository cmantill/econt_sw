nohup python3.6 zmq_server.py --addr 0x20 --server 5554 >& logs/asicServer.log &
nohup python3.6 zmq_server.py --addr 0x21 --server 5555 >& logs/emulatorServer.log &
