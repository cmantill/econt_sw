python3 testing/i2c_single_register.py --rw RW --block PLL_ALL --register pll_bytes_1to0 --parameter enableDes,enableSer --value 0,1
python3 testing/i2c_single_register.py --rw RW --block PLL_ALL --register pll_bytes_17to13 --parameter fromMemToLJCDR_CBOvcoCapSelect --value 496
python3 testing/i2c_single_register.py --rw RW --block PLL_ALL --register pll_bytes_24to22 --parameter toclkgen_disDES --value 1
python3 testing/i2c_single_register.py --rw RW --block PLL_ALL --register pll_bytes_26to25 --parameter ref_clk_sel --value 1
