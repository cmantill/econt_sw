SNAPSHOT="${1:-4}"
EMULATOR_DELAY="${2:-4}"
PHASESELECT="${3:-0}"

echo "starting alignment procedures"
python testing/uhal/align_on_tester.py --step test-data --dtype PRBS28
# or
# python testing/uhal/align_on_tester.py --step test-data --idir configs/test_vectors/counterPatternInTC/RPT/

python3 testing/i2c.py --yaml configs/align.yaml --write --quiet
python3 testing/i2c.py --yaml configs/align.yaml --i2c emulator --write --quiet

echo $PHASESELECT

if [ $PHASESELECT -eq 0 ]; then
    echo "keeping the same trackMode"
    python3 testing/i2c.py --name EPRXGRP_TOP_trackMode 
elif [ $PHASESELECT -eq 99 ]; then
    python3 testing/i2c.py --name EPRXGRP_TOP_trackMode --value 1
else
    python3 testing/i2c.py --name EPRXGRP_TOP_trackMode --value 0
    python3 testing/i2c.py --name CH_EPRXGRP_[0-11]_phaseSelect --value $PHASESELECT
fi

python3 testing/i2c.py --name ALIGNER_orbsyn_cnt_load_val,ALIGNER_orbsyn_cnt_snapshot --value 0,$SNAPSHOT
python3 testing/i2c.py --name ALIGNER_orbsyn_cnt_load_val,ALIGNER_orbsyn_cnt_snapshot --value 0,$SNAPSHOT --i2c emulator
python testing/uhal/align_on_tester.py --step lr-roct --delay $EMULATOR_DELAY --bxlr 3500

# read hdrmm cntrs right after lr-roct
# python3 testing/phaseSelectHist.py -n 100

python3 testing/i2c.py --yaml configs/align_read.yaml --i2c ASIC,emulator

# reset hdrmm cntrs with lr-roct
# python testing/uhal/align_on_tester.py --step lr-roct 
# python3 testing/i2c.py --name CH_ALIGNER*hdr_mm_cntr
