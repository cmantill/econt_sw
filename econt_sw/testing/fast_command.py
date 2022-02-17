import uhal
import argparse
import logging
logging.basicConfig()

from time import sleep

logger = logging.getLogger('fc')

from utils.fast_command import FastCommands
from utils.uhal_config import *

"""
Send/Read fast commands
"""

if __name__ == "__main__":    
    parser = argparse.ArgumentParser(description='Align links')
    parser.add_argument("-L", "--logLevel", dest="logLevel",action="store",
                        help="log level which will be applied to all cmd : ERROR, WARNING, DEBUG, INFO, NOTICE",default='INFO')
    parser.add_argument('--fc', type=str, required=True, 
                        choices=['chipsync','command-delay'],
                        help='fast command')
    parser.add_argument('--read', action='store_true', default=False, help='read')
    args = parser.parse_args()

    set_logLevel(args)


    try:
        logger.setLevel(args.logLevel)
    except ValueError:
        logging.error("Invalid log level")
        exit(1)

    fc=FastCommands()

    fc.configure_fc(args.read)
    if args.fc=='chipsync':
        fc.chipsync()
    elif args.fc=='command-delay':
        if args.read:
            fc.read_command_delay()
        else:
            fc.set_command_delay()
