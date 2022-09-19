import argparse
from time import sleep
from utils.fast_command import FastCommands

"""
Send/Read fast commands
"""
fc_requests = [
    "link_reset_roct",
    "link_reset_econt",
    "orbit_count_reset",
    "chipsync",
    "count_rst", # reset counters
]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fast commands')
    parser.add_argument('--fc', type=str, choices=fc_requests,
                        help='fast command')
    parser.add_argument('--configure', default=False, action='store_true', help='configure fast commands')
    parser.add_argument('--read', action='store_true', default=False, help='read')
    parser.add_argument('--getBX', action='store_true', default=False, help='find BX a FC is being issued')
    parser.add_argument('--getCounter', action='store_true', default=False, help='find BX a FC is being issued')
    parser.add_argument('--setBX', default=None, type=int,  help='set BX a FC is being issued')
    args = parser.parse_args()

    import logging
    logging.basicConfig()
    logger = logging.getLogger('fc')
    logger.setLevel('INFO')


    fc=FastCommands()
    fc_requests = ["link_reset_roct","link_reset_econt",
                   "orbit_count_reset",
                   "chipsync",
                   "count_rst", # reset counters
               ]

    if args.getBX:
        r=fc.get_bx(args.fc)
        logger.info('%s %i'%(args.fc, r))
    elif not args.setBX is None:
        fc.set_bx(args.fc,args.setBX)
    elif args.getCounter:
        r=fc.get_counter(args.fc)
        logger.info('%s %i'%(args.fc, r))
    elif args.fc in fc_requests:
        if args.read:
            fc.get_counter(args.fc,True)
        else:
            fc.request(args.fc)
    elif args.fc=='command-delay':
        if args.read:
            fc.read_command_delay()
        else:
            fc.set_command_delay()
    elif args.configure:
        fc.configure_fc(args.read)
