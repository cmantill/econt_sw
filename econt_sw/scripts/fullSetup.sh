source scripts/quickASICSetup.sh
source scripts/inputWordAlignment.sh 3 3
python testing/i2c.py --name PLL_phase_of_enable_1G28 --value 4
source scripts/ioAlignment.sh
source scripts/lcAlignment.sh
source scripts/lcEmulatorAlignment.sh
