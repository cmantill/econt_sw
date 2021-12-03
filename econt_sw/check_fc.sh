python3 testing/i2c_single_register.py --i2c ASIC --addr 0  --server 5554  --rw RW --block FCTRL_ALL --register config --parameter EdgeSel_T1,invert_command_rx --value 0,0
python testing/uhal-reset_signals.py --i2c ASIC --reset soft 
python testing/uhal-reset_signals.py --i2c ASIC --reset soft --release True
python3 testing/i2c_single_register.py --i2c ASIC --addr 0  --server 5554  --rw RO  --block PLL_ALL --register pll_read_bytes_2to0 --parameter smState
python3 testing/i2c_single_register.py --i2c ASIC --addr 0  --server 5554  --rw RO --block MISC_ALL --register misc_ro_0 --parameter PUSM_state
python3 testing/i2c_single_register.py --i2c ASIC --addr 0  --server 5554  --rw RO --block FCTRL_ALL --register status --parameter locked,fc_error
