# -*- coding: utf-8 -*-
"""
Created on Mon Jun  1 11:09:05 2020

"""

import pandas as pd
import numpy as np
import json
import glob
from math import log

def make_round(x):
    if x != 0:
        return round(x,-int(log(abs(x),10)))
    else:
        return 0

def make_dict(df, keys, values):
    index=list(set(df.columns)-set([keys, values]))
    df=df.pivot(columns=keys,index=index[0])
    # Get rid of multiindex
    df.columns=df.columns.droplevel(0)
    df_dict=df.to_dict(orient='list')
    return {k:[i for i in v if i is not np.nan] for k,v in df_dict.items()}
                
def read_data(file_path, enc):

    # get sheet names from excel input data file, define name and file extension
    xl = pd.ExcelFile(file_path)
    sheet_names = xl.sheet_names
    if 'Sheet1' in sheet_names: sheet_names.remove('Sheet1')
    col_names = ['scenario', 'region', 'serie', 'year', 'total']


    # load data from all sheets into one dataframe
    data = pd.DataFrame()
    for i in sheet_names:
        df = pd.read_excel(xl,
                           sheet_name=i,
                           skiprows=3,
                           encoding=enc,
                           sort=False)
        df = df.dropna(axis=1, how='all')
        tableName = df.iloc[0,0].split(': ')[1]
        label = df.iloc[1,0].split(': ')[1]
        df.columns = list(df.iloc[2,:])
        if 'Region' not in df: df.insert(1, 'region', 'missing')
        df.columns = col_names
        df = df.iloc[3:,:]
        df['tableName'] = tableName
        df['label'] = label
        data = data.append(df, ignore_index=True)


    # drop nan from dataframe
    data = data.dropna()


    # convert strings with digits to integers
    data.year = pd.to_numeric(data.year, errors='ignore', downcast='integer')
    
    return data


def create_json(df, cats, name, singleLine, outputDir, enc):
    """
    Creates customized json file from a pandas dataframe and saves it with the
    selected naming.
    """

    d = df.reset_index()

    d = d.groupby(cats[:-1]).apply(lambda x: x[['year',
                                        'total']]\
                                   .to_dict('r'))\
                                   .reset_index()\
                                   .rename(columns={0:'indicatorGroupValues'})

    d = d.groupby(cats[:-2]).apply(lambda x: x[['indicatorGroup',
                                        'indicatorGroupValues']]\
                                   .to_dict('r'))\
                                   .reset_index()\
                                   .rename(columns={0:'indicatorGroups'})

    if 'region' in cats:
        d = d.groupby(cats[:-3]).apply(lambda x: x[['region',
                                            'indicatorGroups']]\
                                       .to_dict('r'))\
                                       .reset_index()\
                                       .rename(columns={0:'regions'})

        d = d.groupby(cats[:-4]).apply(lambda x: x[['indicator',
                                            'regions']]\
                                        .to_dict('r'))\
                                        .reset_index()\
                                        .rename(columns={0:'indicators'})

    else:
        d = d.groupby(cats[:-3]).apply(lambda x: x[['indicator',
                                            'indicatorGroups']]\
                                       .to_dict('r'))\
                                       .reset_index()\
                                       .rename(columns={0:'indicators'})

    d['scenarios'] = 'scenarios'
    d = d.groupby(['scenarios']).apply(lambda x: x[['scenario',
                                        'indicators']]\
                                       .to_dict('r'))\
                                       .reset_index()\
                                       .rename(columns={0:'data'})
    d = d.set_index('scenarios')


    with open(outputDir + name + '.js', 'w+', encoding=enc) as file:
        d.to_json(file, force_ascii=False)


    if singleLine:
        js_str = open(outputDir + name + '.js', 'r', encoding=enc).read()
        open(outputDir + name + '.js', 'w', encoding=enc)\
        .write('export default ' + js_str)
    else:
        js_str = open(outputDir + name + '.js', 'r', encoding=enc).read()
        with open(outputDir + name + '.js', 'w', encoding=enc) as file:
            js_str = json.dumps(json.loads(js_str), indent=2)
            file.write('export default ' + js_str)
            
            
def update_json(includeValues, fileName, updateKey, encoding):    
    
    # Read existing json file
    with open(fileName, mode="rb") as f:
        data = json.load(f)
    
    # Make a generator to include only new items
    newItems = (i for i in includeValues if i not in data[updateKey].keys())
    
    # Add new items to the dictionary with value None
    for i in newItems:
        data[updateKey][i] = ""
    
    with open(fileName, 'w', encoding=encoding) as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=2)
