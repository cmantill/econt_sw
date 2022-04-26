SNAPSHOT="${1:-3}"
EMULATOR_DELAY="${2:-3}"
SELECT="${2:-32}"

echo "Starting word alignment"
python testing/eRx.py --tv --dtype PRBS28
python testing/eRx.py --lrAlign --bx $SNAPSHOT --bcr 0 --delay $EMULATOR_DELAY

#python testing/eRx.py --override --select $SELECT

python testing/eRx.py --checkAlign --verbose
python testing/eRx.py --logging -N 1 --sleep 2 
