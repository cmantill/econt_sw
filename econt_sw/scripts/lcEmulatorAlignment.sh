echo "     align comparison"
python testing/align_on_tester.py --step latency
python testing/eTx.py --compare --sleep 1 --nlinks 13
