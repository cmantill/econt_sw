source scripts/quickASICSetup.sh
# python testing/i2c.py --yaml configs/ITA/ITA_defaults.yaml --i2c ASIC,emulator --write --quiet
source scripts/inputWordAlignment.sh 3 3
python testing/i2c.py --name PLL_phase_of_enable_1G28 --value 4
# python testing/i2c.py --name PLL_phase_of_enable_1G28 --value 0
source scripts/ioAlignment.sh
source scripts/lcAlignment.sh
source scripts/lcEmulatorAlignment.sh
