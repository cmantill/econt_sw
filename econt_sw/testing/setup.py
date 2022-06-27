from set_econt import *

def init_action(args):
    startup()
    set_phase(args.board)
    set_phase_of_enable(0)
    set_runbit()
    read_status()

def input_action(args):
    set_fpga()
    word_align(args.bx,args.delay)

def output_action(args):
    io_align()
    output_align()

def bypass_action(args):
    if args.align:
        bypass_align(idir="configs/test_vectors/alignment/",start_ASIC=0,start_emulator=1)
    if args.compare:
        bypass_compare(args.idir)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(f'python testing/setup.py ',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    subparsers = parser.add_subparsers(help='Choose which action to perform.')

    parse_init = subparsers.add_parser('init',help='Set initial configuration of ASIC')
    parse_init.add_argument('--board','-b', required=True, type=int, help='Board number')
    parse_init.set_defaults(action=init_action)

    parse_input = subparsers.add_parser('input',help='Align input words')
    parse_input.add_argument('--bx', dest='bx',default=None,type=int, help='BX to take snapshot in')
    parse_input.add_argument('--delay', dest='delay',default=None,type=int, help='Emulator delay setting for link alignment')
    parse_input.set_defaults(action=input_action)

    parse_output = subparsers.add_parser('output',help='Align output words')
    parse_output.set_defaults(action=output_action)

    parse_bypass = subparsers.add_parser('bypass',help='Use bypass words')
    parse_bypass.add_argument('--align',action='store_true',help='Align')
    parse_bypass.add_argument('--compare',action='store_true',help='Compare ASIC and emulator w directory')
    parse_bypass.add_argument('--idir',dest="idir",default="",type=str,  help='IDIR w inputs and outputs')
    parse_bypass.set_defaults(action=bypass_action)

    args = parser.parse_args()

    if 'action' not in args:
        parser.error('Must choose an action to perform!')

    args.action(args)
