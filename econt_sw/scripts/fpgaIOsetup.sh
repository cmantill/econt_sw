#!/bin/bash
ASIC="${1:-8}"

source env.sh
echo "Configure IO for board " ${ASIC}
python testing/align_on_tester.py --step configure-IO --invertIO

echo "Initialize FC and send 28 bit PRBS data"
python testing/align_on_tester.py --step init
