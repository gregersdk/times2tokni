# -*- coding: utf-8 -*-
"""
Created on Sun May 31 23:42:46 2020

@author: Olex
"""

import pandas as pd
import glob
import os

# get list of all input data files with certain file name extension
idf_ex = '.xls'
path_list = glob.glob('input/*' + idf_ex)
col_names = ['sheetname', 'new_sheetname', 'filename']
for file_path in path_list:
    idf_n = file_path.split('\\')[1].split('.')[0]
    xl = pd.ExcelFile(file_path)
    sheet_names = xl.sheet_names
    if 'Sheet1' in sheet_names: sheet_names.remove('Sheet1')
    df = pd.DataFrame(sheet_names)
    df[1]=df[0]
    df[2]='tab1'
    df.columns=col_names
    df.to_csv(idf_n + '.csv',index=False)
    
    
