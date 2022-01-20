ECON-T:
 RW:
  CH_ALIGNER_*INPUT_ALL:
   registers:
    config:
     params:
      # enable each channel aligner
      per_ch_align_en:
       param_value: 1
     
  ALIGNER_ALL:
   registers:
    config:
     params:
      # enable snapshot for aligner mode
      i2c_snapshot_en:
       param_value: 0
      snapshot_en:
       param_value: 1
      snapshot_arm:
       param_value: 1
    # define link-reset-ROCT training pattern
    match_pattern_val:
     value: 0x9cccccccaccccccc
    # do not mask bits in training pattern
    match_mask_val:
     value: 0x0000000000000000
    # how many BXs in one orbit?
    orbsyn_cnt_max_val:
     value: 3563
    orbsyn_cnt_load_val:
     value: 0
    orbsyn_cnt_snapshot:
     value: 4

  FMTBUF_ALL:
   registers:
    # sync word to send in every link-reset-ECONT
    tx_sync_word:
     value: 0x122
    buff_t1:
     value: 338 # default for eRx = 13
    buff_t2:
     value: 314 # default for eRx = 13
    buff_t3:  
     value: 25 # default for eRx = 13
    config:
     params:
      # enable all eTX
      eporttx_numen:
       param_value: 13
      use_sum:
       param_value: 0
      stc_type:
       param_value: 0

  MFC_ALGORITHM_SEL_DENSITY:
   registers:
    algo:
     params:
      select:
       # algorithm: start in threshold sum mode
       param_value: 0
      density:
       param_value: 1

  ALGO_THRESHOLD_VAL:
   registers:
    # high threshold to send idles
    threshold_val_*:
     value: [4194303, 4194303, 4194303, 4194303, 4194303, 4194303, 4194303, 4194303,
             4194303, 4194303, 4194303, 4194303, 4194303, 4194303, 4194303, 4194303,
             4194303, 4194303, 4194303, 4194303, 4194303, 4194303, 4194303, 4194303,
             4194303, 4194303, 4194303, 4194303, 4194303, 4194303, 4194303, 4194303,
             4194303, 4194303, 4194303, 4194303, 4194303, 4194303, 4194303, 4194303,
             4194303, 4194303, 4194303, 4194303, 4194303, 4194303, 4194303, 4194303]

  ALGO_DROPLSB:
   registers:
    drop_lsb:
     value: 3
