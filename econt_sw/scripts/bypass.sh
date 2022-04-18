#!/bin/bash
IDIR=$1
TAG=$2
LATENCY="${3:-12}"
BCR="${4:-1}"
python testing/eRx.py --tv --idir ${IDIR} --tv-name bypass --fname testOutput.csv
python testing/align_on_tester.py --step mlatency --lat ${LATENCY}
python testing/i2c.py --name ALIGNER_orbsyn_cnt_load_val --value ${BCR}
python testing/eTx.py --daq --idir ${IDIR} --odir ${TAG}_bypass_3500_bcr${BCR}_lat${LATENCY} --trigger
python testing/eTx.py --capture --lc lc-input,lc-ASIC,lc-emulator --mode BX --bx 3500 --capture --nwords 100 --csv --odir ${TAG}_bypass_3500_bcr${BCR}_lat${LATENCY}
