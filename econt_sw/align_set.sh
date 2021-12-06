for i in {0..11}; do python3 testing/i2c_single_register.py --name CH_ALIGNER_${i}_per_ch_align_en --value 1; done

python3 testing/i2c_single_register.py --name ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,ALIGNER_snapshot_arm --value 0,1,1
python3 testing/i2c_single_register.py --name ALIGNER_match_pattern_val --value 0x9cccccccaccccccc
python3 testing/i2c_single_register.py --name ALIGNER_match_mask_val --value 0x0000000000000000
python3 testing/i2c_single_register.py --name ALIGNER_orbsyn_cnt_max_val --value 3563

python3 testing/i2c_single_register.py --name FMTBUF_tx_sync_word --value 0x122
python3 testing/i2c_single_register.py --name FMTBUF_buff_t1,FMTBUF_buff_t2,FMTBUF_buff_t3 --value 338,314,25
python3 testing/i2c_single_register.py --name FMTBUF_eporttx_numen,FMTBUF_stc_type,FMTBUF_mask_ae --value 13,0,0

python3 testing/i2c_single_register.py --name MFC_mux_select_0,MFC_mux_select_1,MFC_mux_select_2,MFC_mux_select_3,MFC_mux_select_4,MFC_mux_select_5,MFC_mux_select_6,MFC_mux_select_7 --value 7,4,5,6,3,1,0,2
python3 testing/i2c_single_register.py --name MFC_mux_select_8,MFC_mux_select_9,MFC_mux_select_10,MFC_mux_select_11,MFC_mux_select_12,MFC_mux_select_13,MFC_mux_select_14,MFC_mux_select_15 --value 8,9,10,11,14,13,12,15
python3 testing/i2c_single_register.py --name MFC_mux_select_16,MFC_mux_select_17,MFC_mux_select_18,MFC_mux_select_19,MFC_mux_select_20,MFC_mux_select_21,MFC_mux_select_22,MFC_mux_select_23 --value 23,20,21,22,19,17,16,18
python3 testing/i2c_single_register.py --name MFC_mux_select_24,MFC_mux_select_25,MFC_mux_select_26,MFC_mux_select_27,MFC_mux_select_28,MFC_mux_select_29,MFC_mux_select_30,MFC_mux_select_31 --value 25,24,26,27,30,31,28,29
python3 testing/i2c_single_register.py --name MFC_mux_select_32,MFC_mux_select_33,MFC_mux_select_34,MFC_mux_select_35,MFC_mux_select_36,MFC_mux_select_37,MFC_mux_select_38,MFC_mux_select_39 --value 38,37,39,46,36,34,33,35
python3 testing/i2c_single_register.py --name MFC_mux_select_40,MFC_mux_select_41,MFC_mux_select_42,MFC_mux_select_43,MFC_mux_select_44,MFC_mux_select_45,MFC_mux_select_46,MFC_mux_select_47 --value 40,32,41,42,47,45,43,44

python3 testing/i2c_single_register.py --name MFC_cal_0,MFC_cal_1,MFC_cal_2,MFC_cal_3,MFC_cal_4,MFC_cal_5,MFC_cal_6,MFC_cal_7 --value 348,347,335,336,347,348,335,335
python3 testing/i2c_single_register.py --name MFC_cal_8,MFC_cal_9,MFC_cal_10,MFC_cal_11,MFC_cal_12,MFC_cal_13,MFC_cal_14,MFC_cal_15 --value 323,323,311,311,325,324,312,314
python3 testing/i2c_single_register.py --name MFC_cal_16,MFC_cal_17,MFC_cal_18,MFC_cal_19,MFC_cal_20,MFC_cal_21,MFC_cal_22,MFC_cal_23 --value 307,293,304,318,280,267,279,291
python3 testing/i2c_single_register.py --name MFC_cal_24,MFC_cal_25,MFC_cal_26,MFC_cal_27,MFC_cal_28,MFC_cal_29,MFC_cal_30,MFC_cal_31 --value 303,290,302,315,329,316,328,340
python3 testing/i2c_single_register.py --name MFC_cal_32,MFC_cal_33,MFC_cal_34,MFC_cal_35,MFC_cal_36,MFC_cal_37,MFC_cal_38,MFC_cal_39 --value 263,276,274,261,289,302,300,287
python3 testing/i2c_single_register.py --name MFC_cal_40,MFC_cal_41,MFC_cal_42,MFC_cal_43,MFC_cal_44,MFC_cal_45,MFC_cal_46,MFC_cal_47 --value 286,299,298,286,261,274,274,262

python3 testing/i2c_single_register.py --name MFC_ALGORITHM_SEL_DENSITY_algo_select,MFC_ALGORITHM_SEL_DENSITY_algo_density --value 0,1

python3 testing/i2c_single_register.py --name ALGO_drop_lsb --value 3

for i in {0..47}; do python3 testing/i2c_single_register.py --name ALGO_threshold_val_${i} --value 47; done;

python3 testing/i2c_single_register.py --name ALIGNER_orbsyn_cnt_load_val,ALIGNER_orbsyn_cnt_snapshot --value 0,3
