import pandas as pd
import numpy as np

def parseInputERXdata(inputDir, fName='testInput.csv'):
    df = pd.read_csv(f'{inputDir}/{fName}')

    tc_0 = (np.vectorize(int)(df,16) >> 21) & 127
    tc_1 = (np.vectorize(int)(df,16) >> 14) & 127
    tc_2 = (np.vectorize(int)(df,16) >> 7) & 127
    tc_3 = np.vectorize(int)(df,16) & 127

    df[[f'ADC_TC_{i}' for i in range(0,48,4)]] = pd.DataFrame(tc_0,index=df.index)
    df[[f'ADC_TC_{i}' for i in range(1,48,4)]] = pd.DataFrame(tc_1,index=df.index)
    df[[f'ADC_TC_{i}' for i in range(2,48,4)]] = pd.DataFrame(tc_2,index=df.index)
    df[[f'ADC_TC_{i}' for i in range(3,48,4)]] = pd.DataFrame(tc_3,index=df.index)

    return df[[f'ADC_TC_{i}' for i in range(48)]]


if __name__=='__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--inputDir', default = 'counterPattern_Oct8', dest="inputDir", help="Input directory containing eRx data")
    parser.add_argument('--fileName', default = 'testInput.csv', dest="fName", help="Name of csv file (default: testInput.csv)")
    parser.add_argument('-v', '--verbose', default = False, action='store_true', dest="verbose", help="Verbose output, print all data to screen")

    args = parser.parse_args()

    df = parseInputERXdata(inputDir=args.inputDir,
                           fName = args.fName)

    if args.verbose:
        vals = df.values
        for i, v in enumerate(vals):
            print(i, list(v))
