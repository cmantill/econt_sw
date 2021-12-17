SNAPSHOT="${1:-4}"
EMULATOR_DELAY="${2:-3}"
PHASESELECT="${3:-9}"

echo "PUSM state"
python3 testing/i2c.py --yaml configs/init.yaml >> logs/startupState.log

python3 testing/i2c.py --name PUSM_state

python3 testing/i2c.py --name FCTRL_EdgeSel_T1 --value 0

python3 testing/i2c.py --name FCTRL_locked

echo ""
echo "Setting PLL manually"
python3 testing/i2c.py --name PLL_ref_clk_sel,PLL_enableCapBankOverride,PLL_CBOvcoCapSelect --value 1,1,100 --quiet
echo "PUSM state"
python3 testing/i2c.py --name PUSM_state

echo ""
echo "starting to send data"
source env.sh
python testing/uhal-align_on_tester.py --step configure-IO --invertIO
python testing/uhal-align_on_tester.py --step init

echo "PUSM state"
python3 testing/i2c.py --name PUSM_state


python3 testing/i2c.py --name MISC_run --value 1

source scripts/inputWordAlignment.sh $SNAPSHOT $EMULATOR_DELAY $PHASESELECT
