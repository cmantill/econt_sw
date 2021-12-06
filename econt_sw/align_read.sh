for i in {0..11}
do
    python3 testing/i2c_single_register.py --name CH_ALIGNER_${i}_snapshot
    python3 testing/i2c_single_register.py --rw RO --block CH_ALIGNER_${i}INPUT_ALL --register select
    python3 testing/i2c_single_register.py --rw RO --block CH_ALIGNER_${i}INPUT_ALL --register status
done
#for i in {0..11}
#do
#    python3 testing/i2c_single_register.py --rw RO --block CH_ALIGNER_${i}INPUT_ALL --register status --parameter prbs_chk_err,orbsyn_fc_err,orbsyn_arr_err,orbsyn_hdr_err,align_seu_err,hdr_mm_err,snapshot_dv,pattern_match
#done
python3 testing/i2c_single_register.py --name ALIGNER_orbsyn_cnt_snapshot     
