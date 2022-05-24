#!/bin/bash
ASIC="${1:-8}"
SNAPSHOTBX="${2:-2}"
DELAY="${3:-1}"
GOODPHASEPLL="${4:-0}"

source scripts/ASICsetup.sh ${ASIC} ${GOODPHASEPLL}
source scripts/fpgaIOsetup.sh
source scripts/inputWordAlignment.sh ${SNAPSHOTBX} ${DELAY}
source scripts/ioAlignment.sh
source scripts/lcAlignment.sh
source scripts/lcEmulatorAlignment.sh
