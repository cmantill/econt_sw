#!/bin/bash
ASIC="${1:-8}"
GOODPHASEPLL="${2:-4}"
GOODSELECT="${3:-56}"

source scripts/ASICSetup.sh ${ASIC} ${GOODPHASEPLL} ${GOODSELECT}
source scripts/fpgaIOsetup.sh ${ASIC}
source scripts/inputWordAlignment.sh 3 3
source scripts/ioAlignment.sh
source scripts/lcAlignment.sh
source scripts/lcEmulatorAlignment.sh
