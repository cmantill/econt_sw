import argparse

import logging
logging.basicConfig()
logger = logging.getLogger('fc')
logger.setLevel('INFO')

from time import sleep

from utils.fast_command import FastCommands

"""
Send/Read fast commands
"""

if __name__ == "__main__":    
    parser = argparse.ArgumentParser(description='Fast commands')
    parser.add_argument('--fc', type=str, required=True, 
                        choices=['chipsync','command-delay'],
                        help='fast command')
    parser.add_argument('--read', action='store_true', default=False, help='read')
    args = parser.parse_args()

    fc=FastCommands()
    fc.configure_fc(args.read)
    
    if args.fc=='chipsync':
        fc.request('chipsync')
    elif args.fc=='command-delay':
        if args.read:
            fc.read_command_delay()
        else:
            fc.set_command_delay()
