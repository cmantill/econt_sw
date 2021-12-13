import argparse
import os

import logging
logging.basicConfig()

logger = logging.getLogger("test-i2c")
logger.setLevel(logging.INFO)

import zmq_controller as zmqctrl

"""
Testing reset signals
- Hard reset: Set i2c registers, send reset, check that i2c registers are cleared and release reset.
- Soft reset: Set i2c registers, send reset, check that i2c registers are the same and release reset.

Usage: python3 testing/resets.py --i2c ASIC emulator --server 5554,5555 --reset hard
"""

if __name__ == "__main__":    
    parser = argparse.ArgumentParser(description='Align links')
    parser.add_argument('--server', type=str, default='5554', help='list of i2c server ports - e.g. 5554 for ASIC, 5555 for emulator')
    parser.add_argument('--i2c',  type=str, nargs="+", choices=['ASIC', 'emulator'], help="keys of i2c addresses")
    parser.add_argument('--reset',  type=str, choices=['hard', 'soft'], help="type of reset signal")
    args = parser.parse_args()
    
    # declare boards,addresses and servers
    i2ckeys = args.i2c
    servers = [int(server) for server in args.server.split(',')]
    if len(servers) != len(i2ckeys):
        raise ValueError("Number of servers must be the same as i2c keys")
    duplicates = set([x for x in servers if servers.count(x) >1])
    if len(duplicates)>0:
        raise ValueError("Dupicated servers")

    server={}; 
    addr={'ASIC':0, 'emulator':1}
    for k,key in enumerate(i2ckeys):
        server[key] = str(servers[k])
    logger.info('Servers %s',server)

    # start servers
    env = os.environ.copy()
    from subprocess import PIPE, Popen
    cmds = {}
    cwds = {}
    for key in i2ckeys:
        cmds[key] = ['python3', '-u', 'zmq_server.py', '--addr', '%i'%(0x20+addr[key]), '--server', server[key]]
        cwds[key] = './zmq_i2c'

    for key in i2ckeys:
        logger.info('Starting reset %s test'%key)
        proc = Popen(cmds[key], cwd=cwds[key],stdout=PIPE, universal_newlines=True, env=env)
        i2c_socket = zmqctrl.i2cController("localhost", str(server[key]))

        # write one i2c register (tx_sync_word) 
        import collections
        tx_sync_word = 0b00100100010
        config = {'ECON-T':{'RW':{'FMTBUF_ALL':{'registers':{'tx_sync_word':{'value': tx_sync_word
                                                                         }}}}}}
        i2c_socket.configure(yamlNode=config) # no filename, and just config
        #logger.debug(f'Wrote tx_sync_word: {tx_sync_word:02x}')

        # send reset signal
        os.system('python testing/uhal-reset_signals.py --i2c %s --reset %s'%(key,args.reset))
        
        # read i2c register back
        config['ECON-T']['RW']['FMTBUF_ALL']['registers']['tx_sync_word']['value'] = 0
        
        if args.reset=='hard':
            try:
                read_config = i2c_socket.read_config(yamlNode=config)
            except:
                logger.info('Not able to read i2c after hard reset - releasing')
            else:
                logger.warning('i2c still active after hard reset')

        if args.reset=='soft':
            try: 
                read_config = i2c_socket.read_config(yamlNode=config)
            except:
                logger.warning('Not able to read i2c after soft reset')
            else:
                read_word = read_config['RW']['FMTBUF_ALL']['tx_sync_word']
                #logger.debug(f'Read tx_sync_word: {read_word:02x}')
                if read_word != tx_sync_word:
                    logger.warning('TX Sync word changed after soft reset')

        # release reset
        os.system('python testing/uhal-reset_signals.py --i2c %s --reset %s --release True'%(key,args.reset))
        logger.info('Released %s reset, eTx, eRx alignment required'%args.reset)

        # terminate process
        proc.terminate()
