python testing/uhal/align_on_tester.py --step debug-lcASIC --sync 0x7ff
python3 testing/i2c.py --name FMTBUF_tx_sync_word --value 0x7ff
python testing/uhal/align_on_tester.py --step capture --mode linkreset_ECONt
