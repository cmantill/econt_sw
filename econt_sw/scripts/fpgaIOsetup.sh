#!/bin/bash
echo ""
echo "Starting to send 28 bit PRBS data"
source env.sh
python testing/align_on_tester.py --step configure-IO --invertIO
python testing/align_on_tester.py --step init
