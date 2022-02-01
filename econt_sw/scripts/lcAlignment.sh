echo "Starting link capture alignment"
echo "     send link reset ECONT"
python3 testing/i2c.py --name FMTBUF_tx_sync_word --value 0x122
python testing/uhal/align_on_tester.py --step lr-econt
python testing/uhal/check_align.py --check --block lc-ASIC
python testing/uhal/align_on_tester.py --step capture --lc lc-ASIC --mode linkreset_ECONt
