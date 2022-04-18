#!/bin/bash
ASIC="${1:-8}"
GOODPHASEPLL="${2:-0}"
GOODSELECT="${3:-56}"
PLLCAP="${4:-15}"

source scripts/ASICsetup.sh ${ASIC} ${GOODPHASEPLL} ${GOODSELECT} ${PLLCAP}
source scripts/fpgaIOsetup.sh ${ASIC}
source scripts/inputWordAlignment.sh 3 3
source scripts/ioAlignment.sh
source scripts/lcAlignment.sh
source scripts/lcEmulatorAlignment.sh
