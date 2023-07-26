from set_econt import startup,set_phase,set_phase_of_enable,set_runbit,read_status,set_fpga,word_align,output_align,bypass_align,bypass_compare
from PRBS import scan_prbs

def init_action(args):
    set_fpga()
    startup()
    # set_phase(board=args.board,trackMode=0)
    err,best_PhaseSetting=scan_prbs(32,'ASIC',0.01,range(12),True,verbose=True)
    set_phase(best_setting=','.join([str(i) for i in best_PhaseSetting]))

    set_phase_of_enable(0)
    set_runbit()
    read_status()

def input_action(args):
    set_fpga()
    word_align(args.bx,args.delay)

def output_action(args):
    output_align()

def bypass_action(args):
    if args.align:
        bypass_align(idir="configs/test_vectors/alignment/",start_ASIC=0,start_emulator=13)
    if args.compare:
        bypass_compare(args.idir,"./")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(f'python testing/setup.py ',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--board','-b', required=False, default=None, type=int, help='Board number')
    parser.add_argument('--bx', dest='bx',default=None,type=int, help='BX to take snapshot in')
    parser.add_argument('--delay', dest='delay',default=None,type=int, help='Emulator delay setting for link alignment')
    parser.add_argument('--align',action='store_true',help='Align')
    parser.add_argument('--compare',action='store_true',help='Compare ASIC and emulator w directory')
    parser.add_argument('--idir',dest="idir",default="",type=str,  help='IDIR w inputs and outputs')

    subparsers = parser.add_subparsers(help='Choose which action to perform.')

    parse_init = subparsers.add_parser('init',help='Set initial configuration of ASIC')
    parse_init.set_defaults(action=init_action)

    parse_input = subparsers.add_parser('input',help='Align input words')
    parse_input.set_defaults(action=input_action)

    parse_output = subparsers.add_parser('output',help='Align output words')
    parse_output.set_defaults(action=output_action)

    parse_bypass = subparsers.add_parser('bypass',help='Use bypass words')
    parse_bypass.set_defaults(action=bypass_action)

    args = parser.parse_args()

    import logging
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)-6s %(message)s',
                        datefmt='%m-%d-%y %H:%M:%S')

    if 'action' not in args:
        init_action(args)
        input_action(args)
        output_action(args)
#        bypass_action(args)
    else:        
        args.action(args)
