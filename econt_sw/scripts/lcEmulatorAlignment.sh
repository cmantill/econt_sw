echo "     align comparison"
python testing/uhal/align_on_tester.py --step latency
python testing/uhal/capture.py --compare --sleep 1 --nlinks 13
