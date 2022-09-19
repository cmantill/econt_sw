import yaml
from math import log2,ceil
import re
import os
import json

#cleanup names

#pll bytes name matching
m_pll=re.compile('PLL_pll.*bytes_\d*to\d*_(.*)')
m_pll2=re.compile('PLL_pll.*bytes_\d*_(.*)')

m_ae=re.compile('AUTOENCODER_(\d*)_weights_byte(\d*)')

def fixNames(key):
    newKey=key

    #remove INPUT from name
    if 'INPUT' in key:
        newKey = newKey.replace('INPUT','')

    #remove ALL_ from name
    if 'ALL_' in key:
        newKey = newKey.replace('ALL_','')

    #remove config or status from name
    if 'config_' in key:
        newKey = newKey.replace('config_','')
    if 'status_' in key:
        if not 'phaseSelect' in key: #exception for phaseSelect, which has RO status and RW value
            newKey = newKey.replace('_status_','_')

    # fix MFC names
    if 'MFC_MUX_SELECT' in key:
        newKey = newKey.replace('MFC_MUX_SELECT','MFC')
    if 'MFC_CAL_VAL' in key:
        newKey = newKey.replace('MFC_CAL_VAL','MFC')

    # fix ALGO names
    if 'ALGO_THRESHOLD_VAL' in key:
        newKey = newKey.replace('ALGO_THRESHOLD_VAL','ALGO')
    if 'ALGO_DROPLSB' in key:
        newKey = newKey.replace('ALGO_DROPLSB','ALGO')

    #remove bytes info from PLL names
    if m_pll.match(newKey):
        newKey = f'PLL_{m_pll.match(newKey).groups()[0].replace("fromMemToLJCDR_","")}'
    if m_pll2.match(newKey):
        newKey = f'PLL_{m_pll2.match(newKey).groups()[0].replace("fromMemToLJCDR_","")}'
    if 'PLL_fromFrameAligner' in newKey:
        newKey=newKey.replace('PLL_fromFrameAligner','PLL')

    # fix names of autoencoder registers
    if m_ae.match(newKey):
        v0,v1=m_ae.match(newKey).groups()
        newKey = f'AUTOENCODER_weights_{v0}_{v1}'
    # simplify MISC names
    if 'MISC_misc_rw_0' in newKey:
        newKey = newKey.replace('MISC_misc_rw_0','MISC')
    if 'MISC_misc_ro_0_' in newKey:
        newKey = newKey.replace('MISC_misc_ro_0_','')

    # simplify names of ecc error counters
    if 'ERR_CNT_SINGLE_rw_ecc_err_in_re_' in newKey:
        newKey = newKey.replace('ERR_CNT_SINGLE_rw_ecc_err_in_re_', 'ecc_err_')
    if 'ERR_CNT_DOUBLE_rw_ecc_err_in_re_' in newKey:
        newKey = newKey.replace('ERR_CNT_DOUBLE_rw_ecc_err_in_re_', 'ecc_err_')
    if 'ERR_CNT_PARITY_rw_ecc_err_in_re_' in newKey:
        newKey = newKey.replace('ERR_CNT_PARITY_rw_ecc_err_in_re_', 'ecc_err_')

    #special catch for autoencoder reg doc names:
    if 'AUTOENCODER_[N]_weights_byte' in newKey:
        newKey='AUTOENCODER_weights_[M]_[N]'
    return newKey



def processBlock(registers, rwType, blockName, addr_base, blockDocName):
    outputs={}
    for k in registers.keys():
        reg_info=registers[k]
        regName=''
        regSize=0
        regMask=''
        regAddr=addr_base + (reg_info['addr_offset'] if 'addr_offset' in reg_info else 0)

        kDocName=k
        #if multiple iterations, replace with a list of keys
        if 'n_iterations' in reg_info:
            keylist = [k.replace('*',f'{i}') for i in range(reg_info['n_iterations'])]
            kDocName=k.replace('*','[N]')
            addr_shift=reg_info['addr_shift']
            byteDefault=reg_info['value']
        else:
            keylist=[k]
            byteDefault=[reg_info['value']]
            addr_shift=0

        for i,k_ in enumerate(keylist):
            if 'params' in reg_info:
                p=reg_info['params']
                for j in p.keys():
                    bits=max(ceil(log2(p[j]['param_mask'])),1)
                    shift=p[j]['param_shift']
                    if bits==1:
                        regLoc=f'x[{shift}]'
                    else:
                        regLoc=f'x[{bits+shift-1}:{shift}]'
                    regName=fixNames(f'{blockName}_{k_}_{j}')
                    regDefault=(byteDefault[i]>>shift)&p[j]['param_mask']
                    docName=fixNames(f'{blockDocName}_{kDocName}_{j}')
                    outputs[regName]={'i2cInfo':[rwType,blockName,k_,j],
                                      'addr':hex(regAddr+addr_shift*i),
                                      'size':bits,
                                      'default':regDefault,
                                      'bits':regLoc,
                                      'docName':docName}
            else:
                regName=fixNames(f'{blockName}_{k_}')
                docName=fixNames(f'{blockDocName}_{kDocName}')
                sizeBytes=reg_info['size_byte'] if 'size_byte' in reg_info else 1
                if 'param_mask' in reg_info:
                    bits=max(ceil(log2(reg_info['param_mask'])),1)
                    shift=reg_info['param_shift']
                    if bits==1:
                        regLoc=f'x[{shift}]'
                    else:
                        regLoc=f'x[{bits+shift-1}:{shift}]'
                else:
                    bits=8*sizeBytes
                    regLoc=f'x[{bits-1}:0]'

                outputs[regName]={'i2cInfo':[rwType,blockName,k_],
                                  'addr':hex(regAddr+addr_shift*i),
                                  'size':bits,
                                  'default':byteDefault[i],
                                  'bits':regLoc,
                                  'docName':docName}
    return outputs

def main():
    inputYamlName="ECON_I2C_params_regmap.yaml"
    outputJSONFile="ECON_I2C_dict.json"
    outputRegisterDocFile="ECON_I2C_reg_description_dict.json"

    with open(inputYamlName) as _f:
        mapping=yaml.safe_load(_f)

    outputs={}
    #process yaml file, reading data
    for rwType in ['RW','RO','WO']:
        for block in mapping['ECON-T'][rwType].keys():
            addr_base=mapping['ECON-T'][rwType][block]['addr_base']
            registers=mapping['ECON-T'][rwType][block]['registers']

            if '*INPUT' in block:
                for i in range(12):
                    blockName=block.replace('*INPUT',f'{i}INPUT')
                    blockDocName=block.replace('*INPUT',f'[N]')
                    blockShift=mapping['ECON-T'][rwType][block]['block_shift']
                    x=processBlock(registers, rwType, blockName, addr_base + i*blockShift,blockDocName)
                    outputs.update(x)
            else:
                x=processBlock(registers, rwType, block, addr_base, block)
                outputs.update(x)

    #list of the register documentation names
    regDocNames={}

    #write output file data, and collect list of all documentation names
    lines='{\n'
    infolines='{\n'

    for k,val in outputs.items():
        lines+=f'    "{k}": {val["i2cInfo"]},\n'
        infolines+=f'    "{k}": {val},\n'
        if not val['docName'] in regDocNames:
            regDocNames[val['docName']]=""
    lines = lines[:-2] + '\n}\n'
    infolines = infolines[:-2] + '\n}\n'

    with open(outputJSONFile,'w') as _testFile:
        _testFile.write(lines.replace("'",'"'))
    with open(outputJSONFile.replace('.json','_info.json'),'w') as _testFile:
        _testFile.write(infolines.replace("'",'"'))

    #open old documentation file if it exists, to read in old register descriptions
    oldDoc={}
    if os.path.exists(outputRegisterDocFile):
        with open(outputRegisterDocFile,'r') as _testFile:
            oldDoc=json.load(_testFile)

    #loop though old register descriptions, and write them into new description dictionary if key exists, otherwise print a warning
    missing='### Present in previous file, not in new version\n'
    anyMissing=False
    for k,val in oldDoc.items():
        if k in regDocNames:
            if not val=="":
                print(k,val)
                regDocNames[k]=val
        else:
            anyMissing=True
            missing += f'#  "{k}": "{val}"\n'

    #write documentation file
    doclines='{\n'
    for k,val in regDocNames.items():
        doclines+=f'    "{k}": "{val}",\n'
    doclines = doclines[:-2] + '\n}\n'

    if anyMissing:
        print(missing)

    with open(outputRegisterDocFile,'w') as _testFile:
        _testFile.write(doclines.replace("'",'"'))


if __name__=="__main__":
    main()
