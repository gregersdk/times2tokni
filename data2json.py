# -*- coding: utf-8 -*-
"""
Originally developed by till@energymodelling.club

"""

#%% import required packages
import pandas as pd
import glob
import os
from string import Template
import re

#%% Set working directory
# Return absolute path to this file
absolute_path = os.path.abspath(__file__)
# Change working directory to this file's directory 
os.chdir(os.path.dirname(absolute_path))

#%% Load functions defined in other files
from defs import read_data, create_json, make_dict

#%% Input and output directories
# Define input and output directories
dirs = {'inputDir': 'input/', 
        'outputDirData': 'output/data/',
        'outputDirCode': 'output/charts/'}

# Ensure input and output directories exist
for i in dirs.keys():
    if not os.path.exists(dirs[i]):
        os.makedirs(dirs[i])

#%% Specify settings
# Encoding
enc = 'utf-8'

# INCLUDE REGIONS: True/False (input data dependant)
include_regions = False

# SingleLine JSON: True/False
singleLine = False

#%% Read specification for processing input data
# Naming / location settings
chartSettings = pd.read_csv(dirs['inputDir']+'dict.csv', encoding=enc)
chartLocation = make_dict(chartSettings, keys='filename', values='chartName')


# list of indictor groups that require an algebraic sign switch
l_as = pd.read_csv(dirs['inputDir']+'algebraic_sign_switch.csv', encoding=enc)
l_as = l_as.serie.tolist()

# load line to bar translation table and make dictionary
l2b = pd.read_csv(dirs['inputDir']+'line2bar_combinations.csv',
                  encoding=enc, index_col=0)

dict_l2b = l2b.bar_indicator.to_dict()

# load indicator group to multiplier translation table and make dictionary
i2m = pd.read_csv(dirs['inputDir']+'share_calculation.csv', encoding=enc)

#%% Read excel files to a DataFrame
# Input data categories
cats = ['scenario',
        'chartName',
        'region',
        'serie',
        'year']

# get list of all input data files with certain file name extension
idf_ex = '.xls'
path_list = glob.glob(dirs['inputDir'] + '*' + idf_ex)

# Create an empty DataFrame
data = pd.DataFrame(columns=cats[-2:])

# Read files one by one and merge the DataFrames 
for file_path in path_list:
    df = read_data(file_path, enc)
    data = data.append(df, ignore_index=True)

# Check for duplicate rows
duplicatedRows = len(data[data.duplicated()].index)

# Drop duplicate rows
if duplicatedRows:
    data.drop_duplicates(inplace=True)
    print('Dropped {} duplicated rows'.format(duplicatedRows))
    
#%% Apply renaming
data = data.merge(chartSettings[['tableName', 'chartName']])

#%% Process the input data
# ...
cols = data.columns[data.columns.isin(cats[1:4])].tolist()

# check if regions exist, else remove from the category list
if not include_regions:
    if 'region' in data.columns: del data['region']
    cats.remove('region')
    cols.remove('region')

# make auxiliary dataframes
df1 = data[cols].drop_duplicates().reset_index(drop=True)
df2 = data[['year']].drop_duplicates().reset_index(drop=True)
df3 = data[['scenario']].drop_duplicates().reset_index(drop=True)
df1['total'] = 0
df2['total'] = 0
df3['total'] = 0

# change algebraic sign for selected indicator groups
for i in l_as:
    data.loc[data.serie.str.contains(i), 'total'] *= -1

# calculate share per scenario and year
data['multiplier'] = data.serie
for i in i2m.tableName.unique():
    dict_i2m = i2m[i2m.tableName==i].set_index(['serie']).multiplier.to_dict()
    data.multiplier.replace(dict_i2m, inplace=True)
data.loc[(data.multiplier.str.isnumeric()==False), 'multiplier'] = 0
data['total_multiplied'] = data.total * data.multiplier

for i in i2m.tableName.unique():
    if i in data.chartName:
        data.loc[(data.chartName==i),
                 'total'] = (data[data.chartName==i]\
                             .groupby(['scenario','year'])\
                             .total_multiplied.transform(lambda x: x / x.sum()))

#Scenarios included in the dataset
scenarioNames = data.scenario.unique()

# create min and max values per chart name, title and label for y axis
data['minY'] = data.total
data.loc[data.minY > 0, 'minY'] = 0
data['maxY'] = data.total
charts = data.groupby(['tableName',
                       'chartName',
                       'label']).agg({'minY':'min','maxY':'max'})
charts = charts.reset_index().to_dict('records')

#%% Load templates

with open('templates/charts.txt', 'r', encoding=enc) as file:
    chartsTemplate = file.read()

with open('templates/singleChart.txt', 'r', encoding=enc) as file:
    singleChartTemplate = file.read()
    
with open('templates/singleChartDiff.txt', 'r', encoding=enc) as file:
    singleChartDiffTemplate = file.read()
    
with open('templates/chartsData.txt', 'r', encoding=enc) as file:
    importChartsDataTemplate = file.read()
    
#%% Print charts code

for k, v in chartLocation.items():

    chartsCode = ''
    chartsDiffCode = ''
    chartsData = ''
    
    # Generator with Charts to include in a file
    fileChartCode = (i for i in charts if i['chartName'] in v)
    
    for i in fileChartCode:
        chartsCode += Template(singleChartTemplate).safe_substitute(
            chartName=i['chartName'],
            chartTitle=i['chartName'],
            label=i['label'],
            minY=str(int(i['minY']*1.5)),
            maxY=str(int(i['maxY']*1.5)))
        
        chartsDiffCode += Template(singleChartDiffTemplate).safe_substitute(
            chartName=i['chartName'],
            chartTitle=i['chartName'],
            label=i['label'],
            minY=str(-1),
            maxY=str(1))
    
    chartsData += Template(importChartsDataTemplate).safe_substitute(
        chartType=k.split('Tab')[0], tabNumber=k.split('Tab')[1])
    
    chartsPage = Template(chartsTemplate).safe_substitute(
        chartsData=chartsData, chartsCode=chartsCode,
        chartsDiffCode=chartsDiffCode)
    
    # Find out location of tab number
    m = re.search(r"\d", k).start()
    fileName = 'ChartsTab' + k[m:]
        
    # create charts text file
    with open(dirs['outputDirCode'] + fileName + '.js', 'w',
              encoding=enc) as file:
        file.write(chartsPage)

#%% create scenarioOptions json file

if include_regions: regionNames = data.region.unique()
with open(dirs['outputDirData'] + 'scenarioCombinations.js', 'w',
          encoding=enc) as file:
    text1 = ''
    count1 = 0
    for i in scenarioNames:
#       i = i.replace("_", " ")
        text1 += ("{ \"id\": " + str(count1) +
                 ", \"name\": \"" + i +
                 "\", \"nameNoOptions\": \"" + i +
                 "\", \"short_description\": \"" + i +
                 "\", \"ultra_short_description\": \"" + i +
                 "\", \"ccs\": false, \"bio\": false" + "},\n")
        count1 += 1
    text2 = ''
    count2 = 0
    if include_regions:
        for i in regionNames:
            i = i.replace("_", " ")
            text2 += ("{ \"id\": " + str(count2) +
                     ", \"name\": \"" + i +
                     "\", \"nameNoOptions\": \"" + i +
                     "\", \"country\": \"" + i +
                     "\", \"short_description\": \"" + i +
                     "\", \"ultra_short_description\": \"" + i +
                     "\", \"ccs\": false, \"bio\": false" + "},\n")
            count2 += 1
        text2 = ',\n' + "regionOptions : [" + '\n' + text2[:-2] + '\n]'
    
    text = ("export default {scenarioCombinations : {" + 
            "scenarioOptions : [" + '\n' + text1[:-2] + '\n' +
            "]" + text2 + "}};")
    file.write(text)

#%%
# populate for missing periods
res = pd.merge(df1, df2, on='total')
res = pd.merge(df3, res, on='total')
data = data.append(res, ignore_index=True, sort=True)


# group by categories and sum the total
data = data.groupby(cats)['total'].sum().reset_index()

#%% Print files with data
#Rename some of the categories
cats[1] = 'indicator'
cats[-2] = 'indicatorGroup'

for k, v in chartLocation.items():
    #Subset dataframe to include relevant charts
    df = data[data['chartName'].isin(v)].rename(
        columns={'chartName': 'indicator',
                 'serie': 'indicatorGroup'})
    
    #Create a json file with subset of charts
    create_json(df, cats, k, singleLine, dirs['outputDirData'], enc)

