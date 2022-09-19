import pandas as pd
import numpy as np
import matplotlib.py as plt

def file(board):
  with open(f'prbs_counters_scan_0.05s_1.2V_{board}board.csv', 'r') as csvfile:
     prbs_data = csv.reader(csvfile, delimiter = ',')

  with open(f'pll_capSelect_scan_1.2V_{board}board.csv', 'r') as csv:
     pll_data = csv.reader(csv, delimiter = ',')

  pll_data = pll_data.rename(columns={'0':'capSelect', '7':'State'})
  pll_data.plot(x='capSelect', y='State', marker='|', linestyle='None')

  for i in range(0, 12):
      prbs_data.plot(y=f'CH_{i}')

  prbs_data = prbs_data.rename(columns={'CH_0':0,
                                      'CH_1':1,
                                      'CH_2':2,
                                      'CH_3':3,
                                      'CH_4':4,
                                      'CH_5':5,
                                      'CH_6':6,
                                      'CH_7':7,
                                      'CH_8':8,
                                      'CH_9':9,
                                      'CH_10':10,
                                      ' CH_11':11})



  prbs_data = np.array(prbs_data)
  a,b = np.meshgrid(np.arange(12), np.arange(15))
  plt.hist2d(a.flatten(), b.flatten(), weights=prbs_data.flatten(), bins=(np.arange(13), np.arange(16)), cmap='bwr');
  plt.colorbar()
  plt.ylabel('Phase Select Setting')
  plt.xlabel('Channel Number')
