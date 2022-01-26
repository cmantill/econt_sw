from i2c import call_i2c
import numpy as np

def checkSnapshots(compare=True, verbose=False, bx=4):
    call_i2c(args_name='ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,CH_ALIGNER_*_per_ch_align_en,ALIGNER_snapshot_arm', args_value='1,1,[0]*12,0')
    call_i2c(args_name='ALIGNER_orbsyn_cnt_snapshot',args_value=f'{bx}')
    call_i2c(args_name='ALIGNER_snapshot_arm', args_value='1')

    x=call_i2c(args_name='CH_ALIGNER_*_snapshot*')

    call_i2c(args_name='ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,CH_ALIGNER_*_per_ch_align_en,ALIGNER_snapshot_arm', args_value='0,1,[1]*12,0')

    snapshots=np.array([x['ASIC']['RO'][f'CH_ALIGNER_{i}INPUT_ALL']['snapshot'] + (x['ASIC']['RO'][f'CH_ALIGNER_{i}INPUT_ALL']['snapshot2']<<(16*8)) for i in range(12)])

    if verbose:
        output=''
        for i in range(12):
            output += '  CH {:02n}: {:048x}\n'.format(i,snapshots[i])
        print(output)
    if compare:
        if len(np.unique(snapshots))==1:
            print(f'All snapshots match : {hex(snapshots[0])}')
            return True
        else:
            #do vertical vote to get 'correct' value
            vote=0
            for i in range(192):
                vote += (((snapshots>>i)&1).sum()>6)<<i
            badSnapshots=np.argwhere(snapshots!=vote)
            errors={i: hex(snapshots[i]) for i in badSnapshots.flatten()}
            print(f'ERROR, vote of snapshots is {hex(vote)}, errors in snapshots : {errors}')

            return False



def get_HDR_MM_CNTR(previous=None):
    x=call_i2c(args_name='CH_ALIGNER_*_hdr_mm_cntr')

    
    counts=np.array([x['ASIC']['RO'][f'CH_ALIGNER_{i}INPUT_ALL']['hdr_mm_cntr'] for i in range(12)])

    if previous is None:
        return counts

    agreement = counts==previous

    if agreement.all():
        print(f'Good counters {counts}')
    else:
        increase=np.argwhere((counts>previous) | counts==65535).flatten()
        print(f'ERROR, Increase in channels {increase}: {counts-previous}')
        print(f'           current values {counts}')

    return counts




from time import sleep
import datetime

# x=get_HDR_MM_CNTR()
# for i in range(100):
#     print('-'*40)
#     print(datetime.datetime.now())
#     checkSnapshots()
#     x=get_HDR_MM_CNTR(x)

#     sleep(15)
    

#checkSnapshots(verbose=True)
x=get_HDR_MM_CNTR()
sleep(5)
print(datetime.datetime.now())
checkSnapshots(verbose=True)
x=get_HDR_MM_CNTR(x)
print('-'*40)
