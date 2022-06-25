from set_econt import *

def init_action(args):
    startup()
    set_phase(args.board)
    set_phase_of_enable(0)
    set_runbit()
    read_status()

def input_action(args):
    word_align(args.bx,args.delay)

def output_action(args):
    output_align()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(f'python testing/setup.py ',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    subparsers = parser.add_subparsers(help='Choose which action to perform.')

    parse_init = subparsers.add_parser('init',help='Set initial configuration of ASIC')
    parse_init.add_argument('--board','-b', required=True, choices=list(phase_by_board.keys()), type=int, help='Board number')
    parse_init.set_defaults(action=init_action)

    parse_input = subparsers.add_parser('input',help='Align input words')
    parse_input.add_argument('--bx', dest='bx',required=True,type=int, help='BX to take snapshot in')
    parse_input.add_argument('--delay', dest='delay',required=True,type=int, help='Emulator delay setting for link alignment')
    parse_input.set_defaults(action=input_action)

    parse_output = subparsers.add_parser('output',help='Align output words')
    parse_output.set_defaults(action=output_action)

    args = parser.parse_args()

    if 'action' not in args:
        parser.error('Must choose an action to perform!')

    args.action(args)
