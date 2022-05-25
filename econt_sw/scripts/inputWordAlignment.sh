SNAPSHOT="${1:-3}"
EMULATOR_DELAY="${2:-3}"
SELECT="${2:-32}"

echo "Starting word alignment"
python testing/eRx.py --lrAlign --bx $SNAPSHOT --bcr 0 --delay $EMULATOR_DELAY --verbose
python testing/eRx.py --logging -N 1 --sleep 2

#python testing/eRx.py --override --select $SELECT
