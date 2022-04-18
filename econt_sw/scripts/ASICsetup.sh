#!/bin/bash
ASIC="${1:-8}"
GOODPHASEPLL="${2:-0}"
GOODSELECT="${3:-56}"

# set edge of FC clock
python3 testing/i2c.py --name FCTRL_EdgeSel_T1 --value 0 --quiet

# set PLL settings
python3 testing/i2c.py --name PLL_ref_clk_sel,PLL_enableCapBankOverride,PLL_CBOvcoCapSelect --value 1,1,15 --quiet

# set phase
python3 testing/set_phase.py --board ${ASIC}

# set select value for word-alignment
python3 testing/i2c.py --name CH_ALIGNER_[0-11]_sel_override_val,CH_ALIGNER_[0-11]_sel_override_en,ALIGNER_orbsyn_cnt_load_val --value [${GOODSELECT}]*12,[1]*12,0 --quiet

# send zeros with threshold sum, max threshold and IDLE word set to 0
python3 testing/i2c.py --name ALGO_threshold_val_[0-47],FMTBUF_eporttx_numen --value [0x3fffff]*48,13 --quiet
python3 testing/i2c.py --name FMTBUF_tx_sync_word,ALGO_drop_lsb --value 0,1 --quiet

# set run bit to 1
python3 testing/i2c.py --name MISC_run --value 1 --quiet

# set phase of enable for PLL
python3 testing/i2c.py --name PLL_phase_of_enable_1G28 --value ${GOODPHASEPLL} --quiet

# read back PUSM state and FC locked
echo "FC locked"
python3 testing/i2c.py --name FCTRL_locked
echo "PUSM state"
python3 testing/i2c.py --name PUSM_state
