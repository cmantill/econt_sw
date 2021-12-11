python3 testing/i2c.py --yaml configs/init.yaml
python3 testing/i2c.py --name PLL_ref_clk_sel,PLL_enableCapBankOverride,PLL_CBOvcoCapSelect --value 1,1,100
source env.sh
python testing/uhal-align_on_tester.py --step configure-IO --invertIO
python testing/uhal-align_on_tester.py --step init
python3 testing/i2c.py --name MISC_run --value 1
python3 testing/i2c.py --yaml configs/init.yaml
