echo "Starting link capture alignment"
echo "     send link reset ECONT"
python testing/i2c.py --name FMTBUF_tx_sync_word --value 0x122
python testing/align_on_tester.py --step lr-econt
python testing/check_block.py --check --block lc-ASIC
python testing/eTx.py --capture --lc lc-ASIC --mode linkreset_ECONt --capture --csv
