from i2c import call_i2c
import numpy as np
import argparse

def readSnapshot(i2c='ASIC',return_status=False):
    x=call_i2c(args_yaml='configs/align_read.yaml', args_i2c=i2c)
    snapshots=np.array([x[i2c]['RO'][f'CH_ALIGNER_{i}INPUT_ALL']['snapshot'] + (x[i2c]['RO'][f'CH_ALIGNER_{i}INPUT_ALL']['snapshot2']<<(16*8)) for i in range(12)])
    status=np.array([x[i2c]['RO'][f'CH_ALIGNER_{i}INPUT_ALL']['status'] for i in range(12)])
    if return_status:
        return snapshots, status
    else:
        return snapshots

def checkWordAlignment(verbose=False):
    snapshots_ASIC, status_ASIC=readSnapshot('ASIC', True)
    snapshots_Emulator, status_Emulator=readSnapshot('emulator', True)

    goodASIC=(status_ASIC==3).all()
    goodEmulator=(status_ASIC==2).all() & (snapshots_Emulator=='0xacccccccacccccccacccccccaccccccc9cccccccaccccccc').all()

    if not goodASIC:
        print('ERROR:')
    return status_ASIC, snapshots_ASIC, status_Emulator, snapshots_Emulator

def checkSnapshots(compare=True, verbose=False, bx=4):
    call_i2c(args_name='ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,CH_ALIGNER_*_per_ch_align_en,ALIGNER_snapshot_arm', args_value='1,1,[0]*12,0')
    call_i2c(args_name='ALIGNER_orbsyn_cnt_snapshot',args_value=f'{bx}')
    call_i2c(args_name='ALIGNER_snapshot_arm', args_value='1')
    snapshots=readSnapshot()
    call_i2c(args_name='ALIGNER_i2c_snapshot_en,ALIGNER_snapshot_en,CH_ALIGNER_*_per_ch_align_en,ALIGNER_snapshot_arm', args_value='0,1,[1]*12,0')


    if verbose:
        output=''
        for i in range(12):
            output += '  CH {:02n}: {:048x}\n'.format(i,snapshots[i])
        print(output)
    if compare:
        if len(np.unique(snapshots))==1:
            if verbose:
                print(f'All snapshots match : {hex(snapshots[0])}')
            return True
        else:
            #do vertical vote to get 'correct' value
            if verbose:
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

    agreement = (counts==previous) & ~(counts==65535)

    if agreement.all():
        print(f'Good counters {counts}')
    else:
        increase=np.argwhere((counts>previous) | (counts==65535)).flatten()
        print(f'ERROR, Increase in channels {increase}: {counts-previous}')
        print(f'           current values {counts}')

    return counts




from time import sleep
import datetime

def statusLogging(sleepTime=120, N=30):
    x=get_HDR_MM_CNTR()

    for i in range(N):
        sleep(sleepTime)
        print('-'*40)
        print(datetime.datetime.now())
        checkSnapshots()
        x=get_HDR_MM_CNTR(x)



if __name__=='__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--logging', dest='runLogging',default=False, action='store_true')
    parser.add_argument('--snapshot', dest='getSnapshot',default=False, action='store_true')
    parser.add_argument('--hdrMM', dest='getHdrMM',default=False, action='store_true')
    parser.add_argument('--alignment', dest='checkWordAlignment',default=False, action='store_true')
    parser.add_argument('-N',dest='N',default=1,type=int,help='Number of iterations to run')
    parser.add_argument('--sleep',dest='sleepTime',default=120,type=int,help='Time to wait between logging iterations')
    parser.add_argument('--verbose', dest='verbose',default=False, action='store_true')

    args = parser.parse_args()

    if args.runLogging:
        statusLogging(sleepTime=args.sleepTime, N=args.N)

    if args.getSnapshot:
        checkSnapshots(verbose=args.verbose)

    if args.checkWordAlignment:
        checkWordAlignment(verbose=args.verbose)

    if args.getHdrMM:
        x=get_HDR_MM_CNTR()
        print(x)

# #checkSnapshots(verbose=True)
# x=get_HDR_MM_CNTR()
# sleep(15)
# print(datetime.datetime.now())
# checkSnapshots(verbose=True)
# x=get_HDR_MM_CNTR(x)
# print('-'*40)


