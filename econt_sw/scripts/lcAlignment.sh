echo "Starting link capture alignment"
echo "     send link reset ECONT"
python3 testing/i2c.py --name FMTBUF_tx_sync_word --value 0x122
python3 testing/align_on_tester.py --step lr-econt
python3 testing/check_align.py --check --block lc-ASIC
python3 testing/capture.py --lc lc-ASIC --mode linkreset_ECONt --capture
