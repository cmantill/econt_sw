echo "Starting link capture alignment"
echo "     send link reset ECONT"
python testing/i2c.py --name FMTBUF_tx_sync_word,FMTBUF_eporttx_numen --value 0x122,0xd --quiet
python testing/align_on_tester.py --step lr-econt
python testing/check_block.py --check --block lc-ASIC
python testing/eTx.py --capture --lc lc-ASIC --mode linkreset_ECONt --capture --csv
