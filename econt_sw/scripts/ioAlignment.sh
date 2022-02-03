ALGO="${1:-0}"
THRESHOLD="${2:-0x3fffff}"
python3 testing/i2c.py --name MFC_ALGORITHM_SEL_DENSITY_algo_select --value $ALGO --i2c ASIC,emulator --quiet
python3 testing/i2c.py --name ALGO_threshold_val_[0-47] --value $THRESHOLD --i2c ASIC,emulator --quiet
python3 testing/i2c.py --name FMTBUF_eporttx_numen --value 13

python testing/uhal/align_on_tester.py --step configure-IO --invertIO
python testing/uhal/test_vectors.py
python testing/uhal/check_align.py --check --block from-IO
