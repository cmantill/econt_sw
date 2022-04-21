#!/bin/bash
source env.sh
echo "Configure IO"
python testing/align_on_tester.py --step configure-IO --invertIO

echo "Initialize FC and send 28 bit PRBS data"
python testing/align_on_tester.py --step init
