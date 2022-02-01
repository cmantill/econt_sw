SELECT="${1:-0x40}"
SNAPSHOT="${1:-4}"
EMULATOR_DELAY="${2:-4}"

echo "Reading alignment status on ASIC"
python3 testing/i2c.py --yaml configs/align_read.yaml --i2c ASIC

echo "Manual alignment mode"
python3 testing/i2c.py --name ALIGNER_snapshot_en --value 1
python3 testing/i2c.py --name CH_ALIGNER_*_per_ch_align_en --value 0
python3 testing/i2c.py --name ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_arm --value 0,0

python3 testing/i2c.py --name CH_ALIGNER_*_sel_override_val --value $SELECT
python3 testing/i2c.py --name CH_ALIGNER_*_sel_override_en --value 1

echo "Take snapshot with link reset ROCT - this should reset the hdr_mm_cntr but hopefully do not modify the alignment?"
python3 testing/i2c.py --name ALIGNER_orbsyn_cnt_load_val,ALIGNER_orbsyn_cnt_snapshot --value 0,$SNAPSHOT
python3 testing/i2c.py --name CH_ALIGNER*hdr_mm_cntr 
python testing/uhal/align_on_tester.py --step lr-roct --delay $EMULATOR_DELAY --bxlr 3500
python3 testing/i2c.py --name CH_ALIGNER*hdr_mm_cntr

echo "Reading alignment status back"
python3 testing/i2c.py --yaml configs/align_read.yaml --i2c ASIC,emulator
