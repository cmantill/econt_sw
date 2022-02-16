echo "     align comparison"
python3 testing/align_on_tester.py --step latency
python3 testing/capture.py --compare --sleep 1 --nlinks 13
