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
                        help='fast command')
    parser.add_argument('--read', action='store_true', default=False, help='read')
    args = parser.parse_args()

    fc=FastCommands()    
    fc_requests = ["link_reset_roct","link_reset_econt",
                   "orbit_count_reset",
                   "chipsync",
                   "count_rst", # reset counters
               ]
    if args.fc in fc_requests:
        if args.read:
            fc.get_counter(args.fc,True)
        else:
            fc.request(args.fc)
    elif args.fc=='command-delay':
        if args.read:
            fc.read_command_delay()
        else:
            fc.set_command_delay()
    elif args.fc=='configure':
        fc.configure_fc(args.read)
