SNAPSHOT="${1:-4}"
EMULATOR_DELAY="${2:-4}"
PHASESELECT="${3:-0}"

echo "starting alignment procedures"
python testing/eRx.py --tv --dtype PRBS28
# or
# python testing/test_vectors.py --idir . configs/test_vectors/counterPatternInTC/RPT/

python testing/i2c.py --yaml configs/align.yaml --write --quiet
python testing/i2c.py --yaml configs/align.yaml --i2c emulator --write --quiet

# echo $PHASESELECT

if [ $PHASESELECT -eq 0 ]; then
    echo "keeping the same trackMode"
    python testing/i2c.py --name EPRXGRP_TOP_trackMode 
elif [ $PHASESELECT -eq 99 ]; then
    python testing/i2c.py --name EPRXGRP_TOP_trackMode --value 1
else
    python testing/i2c.py --name EPRXGRP_TOP_trackMode --value 0
    python testing/i2c.py --name CH_EPRXGRP_[0-11]_phaseSelect --value $PHASESELECT
fi

python testing/i2c.py --name ALIGNER_orbsyn_cnt_load_val,ALIGNER_orbsyn_cnt_snapshot --value 0,$SNAPSHOT
python testing/i2c.py --name ALIGNER_orbsyn_cnt_load_val,ALIGNER_orbsyn_cnt_snapshot --value 0,$SNAPSHOT --i2c emulator

python testing/align_on_tester.py --step lr-roct --delay $EMULATOR_DELAY --bxlr 3500

python testing/i2c.py --yaml configs/align_read.yaml --i2c ASIC,emulator

python testing/eRx.py --alignment --verbose
python testing/eRx.py --logging -N 1 --sleep 2
