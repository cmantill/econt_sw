#!/bin/bash
ASIC="${1:-3}"
GOODPHASEPLL="${2:-0}"
GOODSELECT="${3:-56}"

python3 testing/i2c.py --name FCTRL_EdgeSel_T1 --value 0 --quiet
python3 testing/i2c.py --name PLL_ref_clk_sel,PLL_enableCapBankOverride,PLL_CBOvcoCapSelect --value 1,1,100 --quiet

echo "Setting up ASIC board ${ASIC}"
if [ $ASIC -eq 2 ]; then
    python3 testing/i2c.py --name EPRXGRP_TOP_trackMode,CH_EPRXGRP_[0-11]_phaseSelect --value 0,6,6,7,7,7,8,7,8,7,8,7,8 --quiet
fi
if [ $ASIC -eq 3 ]; then
    # python3 testing/i2c.py --name EPRXGRP_TOP_trackMode,CH_EPRXGRP_[0-11]_phaseSelect --value 0,7,6,8,7,0,8,8,0,8,8,9,8 --quiet
    python3 testing/i2c.py --name EPRXGRP_TOP_trackMode,CH_EPRXGRP_[0-11]_phaseSelect --value 0,7,6,8,7,0,8,8,0,8,8,8,8 --quiet
fi

python3 testing/i2c.py --name CH_ALIGNER_[0-11]_sel_override_val,CH_ALIGNER_[0-11]_sel_override_en,ALIGNER_orbsyn_cnt_load_val --value [${GOODSELECT}]*12,[1]*12,0 --quiet

python3 testing/i2c.py --name ALGO_threshold_val_[0-47],FMTBUF_eporttx_numen --value [0x3fffff]*48,13 --quiet
python3 testing/i2c.py --name FMTBUF_tx_sync_word,ALGO_drop_lsb --value 0,1 --quiet

python3 testing/i2c.py --name MISC_run --value 1 --quiet

python3 testing/i2c.py --name PLL_phase_of_enable_1G28 --value ${GOODPHASEPLL} --quiet

echo "PUSM state"
python3 testing/i2c.py --name PUSM_state
