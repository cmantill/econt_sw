#for i in {0..11}; do python3 testing/i2c_single_register.py --name CH_ALIGNER_${i}_per_ch_align_en --value 1; done
python3 testing/DN_i2c_single_register.py --name CH_ALIGNER_[0-11]_per_ch_align_en --value 1

python3 testing/i2c_single_register.py --name ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,ALIGNER_snapshot_arm --value 0,1,1
python3 testing/i2c_single_register.py --name ALIGNER_match_pattern_val --value 0x9cccccccaccccccc
python3 testing/i2c_single_register.py --name ALIGNER_match_mask_val --value 0x0000000000000000
python3 testing/i2c_single_register.py --name ALIGNER_orbsyn_cnt_max_val --value 3563

python3 testing/i2c_single_register.py --name FMTBUF_tx_sync_word --value 0x122
python3 testing/i2c_single_register.py --name FMTBUF_buff_t1,FMTBUF_buff_t2,FMTBUF_buff_t3 --value 338,314,25
python3 testing/i2c_single_register.py --name FMTBUF_eporttx_numen,FMTBUF_stc_type,FMTBUF_mask_ae --value 13,0,0

python3 testing/i2c_single_register.py --name MFC_ALGORITHM_SEL_DENSITY_algo_select,MFC_ALGORITHM_SEL_DENSITY_algo_density --value 0,1

python3 testing/i2c_single_register.py --name ALGO_drop_lsb --value 3

python3 testing/i2c_single_register.py --name ALIGNER_orbsyn_cnt_load_val,ALIGNER_orbsyn_cnt_snapshot --value 0,3
