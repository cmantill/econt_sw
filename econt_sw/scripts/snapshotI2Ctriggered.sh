python3 testing/i2c.py --name ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,CH_ALIGNER_*_per_ch_align_en,ALIGNER_snapshot_arm --value 1,1,[0]*12,0 --quiet
python3 testing/i2c.py --name ALIGNER_snapshot_arm --value 1 --quiet
python3 testing/i2c.py --name CH_ALIGNER_*_snapshot

python3 testing/i2c.py --name ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,CH_ALIGNER_*_per_ch_align_en,ALIGNER_snapshot_arm --value 0,1,[1]*12,0 --quiet
