SNAPSHOT="${1:-4}"
EMULATOR_DELAY="${2:-4}"

echo "Starting word alignment"
python testing/eRx.py --tv --dtype PRBS28

python testing/i2c.py --yaml configs/align.yaml --write --quiet
python testing/i2c.py --yaml configs/align.yaml --i2c emulator --write --quiet
python testing/i2c.py --name ALIGNER_orbsyn_cnt_load_val,ALIGNER_orbsyn_cnt_snapshot --value 1,$SNAPSHOT --quiet
python testing/i2c.py --name ALIGNER_orbsyn_cnt_load_val,ALIGNER_orbsyn_cnt_snapshot --value 1,$SNAPSHOT --i2c emulator --quiet

python testing/align_on_tester.py --step lr-roct --delay $EMULATOR_DELAY --bxlr 3500

python testing/i2c.py --yaml configs/align_read.yaml --i2c ASIC,emulator

python testing/eRx.py --alignment --verbose
python testing/eRx.py --logging -N 1 --sleep 2
