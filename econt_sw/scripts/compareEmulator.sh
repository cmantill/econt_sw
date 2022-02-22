IDIR="${1}"
for dir in configs/test_vectors/${IDIR}/*/
do
    echo $(basename $dir)
    python testing/eTx.py --daq --idir $dir --trigger
    python testing/eTx.py --capture --fname $(basename $dir) --verbose
done
