import uhal
import argparse
import os

import logging
logging.basicConfig()

logger = logging.getLogger("test-i2c")
logger.setLevel(logging.INFO)

import zmq_controller as zmqctrl

"""
Testing slow control.
- Sets address using uHal.
- Starts server.
- Writes registers.
- Reads and compares registers.

Usage: python3 testing/i2c.py --i2c ASIC emulator --addr 0,1 --server 5554,5555 --set-address

For i2c, the 3 highest bits are 010, and the 4 lowest bits are set for each chip by 4 pins on the chip.
If the voltages on those four pins are, for example, high, low, high, low, then the 4 lowest bits of the I2C address would be 1010, and the whole address would be 0x2A.

To test all possible addresses:
for i in {0..16}; do python3 testing/i2c.py --i2c ASIC emulator --addr $i,1 --server 5554,5555 --set-address; done
"""

if __name__ == "__main__":    
    parser = argparse.ArgumentParser(description='Align links')
    parser.add_argument('--addr', type=str, default='0', help='list of i2c list of addresses - e.g. 0 for ASIC, 1 for emulator')
    parser.add_argument('--server', type=str, default='5554', help='list of i2c server ports - e.g. 5554 for ASIC, 5555 for emulator')
    parser.add_argument('--i2c',  type=str, nargs="+", choices=['ASIC', 'emulator'], help="keys of i2c addresses")
    parser.add_argument('--set-address', type=bool, default=True, help='set i2c address')
    args = parser.parse_args()
    
    # declare boards,addresses and servers
    i2ckeys = args.i2c
    addresses = [int(addr) for addr in args.addr.split(',')]
    servers = [int(server) for server in args.server.split(',')]
    if len(addresses) != len(i2ckeys) or len(servers) != len(i2ckeys):
        raise ValueError("Number of addresses/servers must be the same as i2c keys")
    duplicates = set([x for x in addresses if addresses.count(x) > 1]) or set([x for x in servers if servers.count(x) >1])
    if len(duplicates)>0:
        if 'ASIC' in i2ckeys:
            # manually set address and server if testing ASIC
            addresses = [addr if i==0 else addr+1 for i,addr in enumerate(addresses)]
            servers = [server if i==0 else server+1 for i,server in enumerate(servers)]
            logger.warning('Manually setting addresses to avoid duplicates')
        else:
            raise ValueError("Dupicated addresses or servers")

    addr = {}; server={}; 
    for k,key in enumerate(i2ckeys):
        addr[key] = addresses[k]
        server[key] = str(servers[k])
    logger.info('Addresses %s',addr)
    logger.info('Servers %s',server)

    # test address
    if args.set_address:
        for key in i2ckeys:
            os.system('python testing/uhal-i2c_set_address.py --i2c %s --addr %i'%(key,addr[key]))

    # start servers
    env = os.environ.copy()
    from subprocess import PIPE, Popen
    cmds = {}
    cwds = {}
    for key in i2ckeys:
        cmds[key] = ['python3', '-u', 'zmq_server.py', '--addr', '%i'%(0x20+addr[key]), '--server', server[key]]
        cwds[key] = './zmq_i2c'

    for key in i2ckeys:
        logger.info('Starting i2c %s test'%key)
        proc = Popen(cmds[key], cwd=cwds[key],stdout=PIPE, universal_newlines=True, env=env)
        i2c_socket = zmqctrl.i2cController("localhost", str(server[key]))

        # write one i2c register (tx_sync_word) and read back
        import collections
        tx_sync_word = 0b00100100010
        config = {'ECON-T':{'RW':{'FMTBUF_ALL':{'registers':{'tx_sync_word':{'value': tx_sync_word
                                                                         }}}}}}
        i2c_socket.configure(yamlNode=config) # no filename, and just config
        logger.debug(f'Wrote tx_sync_word: {tx_sync_word:02x}')

        # now read back
        config['ECON-T']['RW']['FMTBUF_ALL']['registers']['tx_sync_word']['value'] = 0
        read_config = i2c_socket.read_config(yamlNode=config)
        read_word = read_config['RW']['FMTBUF_ALL']['tx_sync_word']
        logger.debug(f'Read tx_sync_word: {read_word:02x}')
        if read_word == tx_sync_word:
            logger.info(f'Same tx_sync word for write/read: {read_word:02x}')
            
        # initialize with default config
        i2c_socket.initialize()

        # read back
        i2c_read = i2c_socket.read_and_compare()
        logger.info(f'Unmatched {i2c_read}')        
        i2c_read = i2c_socket.read_and_compare('RO')
        logger.info(f'Unmatched {i2c_read}')

        # terminate process
        proc.terminate()
