# ALGO="${1:-0}"
# THRESHOLD="${2:-0x3fffff}"
# echo ${ALGO}
# echo ${THRESHOLD}

python testing/i2c.py --name MFC_ALGORITHM_SEL_DENSITY_algo_select,ALGO_threshold_val_[0-47],FMTBUF_eporttx_numen,FMTBUF_tx_sync_word --value 0,[0x3fffff]*48,13,0x122 --i2c ASIC,emulator --quiet
python testing/align_on_tester.py --step configure-IO --invertIO
python testing/check_block.py --check --block from-IO
python testing/align_on_tester.py --step manual-IO
