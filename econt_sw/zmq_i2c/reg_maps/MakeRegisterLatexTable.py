import json
import pandas as pd
import numpy as np

with open("ECON_I2C_dict_info.json") as f:
    names_to_register = json.load(f)
try:
    with open("ECON_I2C_reg_description_dict.json") as f:
        registerDescriptions = json.load(f)
except:
    registerDescriptions=None

outputs=[]
for key,item in names_to_register.items():
    outputs.append([key,item['i2cInfo'][0],item['addr'],item['bits'],item['default'],item['docName'],registerDescriptions[item['docName']]])
df=pd.DataFrame(outputs)
df.columns=['Name','Access','Address','Bits','Default','DocName','Description']

df.Address=np.vectorize(int)(df.Address,16)
df=df.sort_values('Address')
df.Address=df.Address.apply(hex)

blocks=['CH_ALIGNER',
   'CH_EPRXGRP',
   'ALIGNER',
   'ERRTOP',
   'EPRXGRP_TOP',
   'FCTRL',
   'FMTBUF',
   'MFC',
   'ALGO',
   'ERX',
   'ETX',
   'PLL',
   'AUTOENCODER',
   'MISC',
   'PUSM',
   'CH_ALIGNER',
   'CH_ERR',
   'CH_EPRXGRP',
]


texInfo="""\\newgeometry{left=1cm,bottom=1cm, top=1cm,right=1cm}
\\begin{landscape}


"""

for blockName in blocks:
    texInfo += "\\begin{longtable}{| l | c | c | r | c | p{0.6\\textwidth} |}\n"
    _name=blockName.replace('_','\_')
    texInfo += "\\caption{Registers for "+_name+" block}\n"
    texInfo += "\\label{"+blockName+"RegistersTable} \\\\\n"
    texInfo += """\\hline
\\textbf{Name}& \\textbf{Access} & \\textbf{Address} & \\textbf{Bits} & \\textbf{Default} & \\textbf{Description} \\\\
\\hline \\hline
\\endhead
\\multicolumn{6}{r}{\\textit{Continued on next page}} \\\\
\\endfoot
\\endlastfoot
"""
    for i in df[df.Name.str.startswith(blockName)].index:
        x=df.loc[i]
        n=x['Name'].replace('_','\_')
        d=x['Description'].replace('_','\_')
        endline='\\\\'
        texInfo += f"      {n} & {x['Access']} & {x['Address']} & {x['Bits']} & {hex(x['Default'])} & {d} {endline}\n"
        texInfo += "      \hline\n"
    texInfo += "\end{longtable}\n\n\n"
texInfo += "\end{landscape}\n"

with open('regTable.tex','w') as _file:
    _file.write(texInfo)
