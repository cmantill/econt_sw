from set_econt import *

if __name__ == "__main__":
    """
    Test ECON-T functionality after time in beam
    """

    parser = argparse.ArgumentParser()
    parser.add_argument('--board','-b', default=12, type=int, help='Board number')
    parser.add_argument('--odir', type=str, default='test/', help='output dir')
    args = parser.parse_args()
    
    # Settings
    board = args.board

    ## Read power (TODO)

    for voltage in [1.2]: #[0.8,1.2,1.32]:
        ## Set voltage and read power (TODO)
        
        ## Initialization
        startup()
        
        ## PRBS phase scan
        from PRBS import scan_prbs
        err_counts, best_setting = scan_prbs(32,'ASIC',120,range(0,12),True,False)
        # save err_counts in pkl file

        ## Scan PLL VCO Cap select and set it back (TODO) 
        for capSelect in range(0,15):
            x=call_i2c(args_name='PLL_CBOvcoCapSelect',args_value=f'{capSelect}',args_i2c='ASIC')
            # which registers to monitor?

        ## Other init steps
        set_phase(board)
        set_phase_of_enable(0)
        set_runbit()
        read_status()
    
        ## Input word alignment
        set_fpga()
        word_align(bx=None,emulator_delay=None)
        
        ## Output
        io_align()
        output_align()
        
        ## Bypass align
        bypass_align(idir="configs/test_vectors/alignment/",start_ASIC=0,start_emulator=1)
        
        ## Compare for various directories
        dirs = [
            "configs/test_vectors/mcDataset/STC_type0_eTx1/",
        ]
        for idir in dirs:
            bypass_compare(idir)

        ## Scan IO delay and save pkl file in odir
        from delay_scan import delay_scan
        delay_scan(odir,io='from')

