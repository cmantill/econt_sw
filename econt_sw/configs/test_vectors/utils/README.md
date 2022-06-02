# Test vectors

## Unpacking

For a given directory, e.g.:
```
/Users/cmantill/ECON/ECONT/TESTING/econt_sw/econt_sw/configs/test_vectors/counterPatternInTC/
```
with input and output files.

For input:
```
python unpack.py --algo input --nrows 20 -i /Users/cmantill/ECON/ECONT/TESTING/econt_sw/econt_sw/configs/test_vectors/counterPatternInTC/testInput.csv
# or
python parseInputs.py --inputDir /Users/cmantill/ECON/ECONT/TESTING/econt_sw/econt_sw/configs/test_vectors/counterPatternInTC/ --fileName testInput.csv -v
```

For Repeater:
```
python unpack.py --algo RPT --nrows 18 -i /Users/cmantill/ECON/ECONT/TESTING/econt_sw/econt_sw/configs/test_vectors/counterPatternInTC/RPT/lc-emulator-Output_header.csv
# or
python parseOutputsRepeater.py --inputDir /Users/cmantill/ECON/ECONT/TESTING/econt_sw/econt_sw/configs/test_vectors/counterPatternInTC/RPT/ --fileName lc-emulator-Output_header.csv -v
```

For Threshold Sum:
```
python unpack.py --algo TS --nrows 1 -i /Users/cmantill/ECON/ECONT/TESTING/econt_sw/econt_sw/configs/test_vectors/randomPatternExpInTC/TS_diffThreshold/lc-emulator-Output_header_SC.csv
```