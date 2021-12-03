python3 testing/i2c_single_register.py --name MISC_run
python3 testing/i2c_single_register.py --name FCTRL_locked,FCTRL_fc_error,FCTRL_command_rx_inverted
python3 testing/i2c_single_register.py --name FCTRL_invert_command_rx,FCTRL_EdgeSel_T1
python3 testing/i2c_single_register.py --name PLL_output_clk_sel,PLL_ref_clk_sel,PLL_VCObypass,PLL_lfEnable
python3 testing/i2c_single_register.py --name PLL_pll_not_locked_timeout,PLL_lfState,PLL_lfLocked,PLL_lfInstLock,PLL_lfLossOfLockCount,PLL_smState,PLL_smLocked
python3 testing/i2c_single_register.py --name PUSM_state
