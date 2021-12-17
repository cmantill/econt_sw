SNAPSHOT="${1:-4}"
EMULATOR_DELAY="${2:-4}"
PHASESELECT="${3:-9}"

echo "starting alignment procedures"
python3 testing/i2c.py --yaml configs/align.yaml --write --quiet
python3 testing/i2c.py --yaml configs/align.yaml --i2c emulator --write --quiet

#python3 testing/i2c.py --name CH_EPRXGRP_[0-11]_phaseSelect --value $PHASESELECT
python3 testing/i2c.py --name EPRXGRP_TOP_trackMode --value 1
python3 testing/i2c.py --name ERX_ch_7_ch_equalizer --value 3

python3 testing/i2c.py --name ALIGNER_orbsyn_cnt_load_val,ALIGNER_orbsyn_cnt_snapshot --value 0,$SNAPSHOT
python3 testing/i2c.py --name ALIGNER_orbsyn_cnt_load_val,ALIGNER_orbsyn_cnt_snapshot --value 0,$SNAPSHOT --i2c emulator
python testing/uhal-align_on_tester.py --step lr-roct --delay $EMULATOR_DELAY --bxlr 3500

python3 testing/i2c.py --yaml configs/align_read.yaml --i2c ASIC,emulator


python3 testing/i2c.py --name CH_ALIGNER*hdr_mm_cntr
sleep 1
python3 testing/i2c.py --name CH_ALIGNER*hdr_mm_cntr
