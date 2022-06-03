import pandas as pd
import numpy as np

def bin32(v, hex=False):
    if hex:
        x=int(v,16)
    else:
        x=v
    return '{0:032b}'.format(x)

def parseOutputRepeater(inputDir, fName='testOutput.csv', asInt=True):
    df = pd.read_csv(f'{inputDir}/{fName}')

    values = df[[f'TX_DATA_{i}' for i in range(11)]].values
    valsBin = np.vectorize(bin32)(values,hex=True)

    # look at header
    dataHeader = np.array([''.join(x)[:5] for x in valsBin])
    dataBX = dataHeader.T.view('<U5').T

    # join data from each line together, dropping first 5 bits (header) and last 11 bits (padded zeros)
    dataStrings = np.array([''.join(x)[5:-11] for x in valsBin])

    # split data into 7 character chunks
    dataTC = dataStrings.T.view('<U7').T.reshape(-1,48)

    if asInt:
        dataBX = np.vectorize(int)(dataBX,2)
        dataTC = np.vectorize(int)(dataTC,2)

    df = pd.DataFrame(dataTC,columns=[f'OUT_TC_{i}' for i in range(48)])
    df['BX'] = dataBX
    
    return df

if __name__=='__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--inputDir', default = 'counterPatternInTC', dest="inputDir", help="Input directory containing eTx data")
    parser.add_argument('--fileName', default = 'testOutput.csv', dest="fName", help="Name of csv file (default: testOutput.csv)")
    parser.add_argument('--asBin', default = False, action='store_true', dest="asBin", help="Return data as binary values")
    parser.add_argument('-v', '--verbose', default = False, action='store_true', dest="verbose", help="Verbose output, print all data to screen")

    args = parser.parse_args()

    df = parseOutputRepeater(inputDir = args.inputDir,
                             fName = args.fName,
                             asInt = not args.asBin)

    if args.verbose:
        vals = df.values
        for i, v in enumerate(vals):
            print(i, list(v))
