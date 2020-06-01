# -*- coding: utf-8 -*-
"""
Created on Fri Nov 30 2019

author: till@energymodelling.club

TODO: encoding for SingleLine=False not working
"""

#%% import required packages
import pandas as pd
import glob
import os

#%% Set working directory
# Return absolute path to this file
absolute_path = os.path.abspath(__file__)
# Change working directory to this file's directory 
os.chdir(os.path.dirname(absolute_path))

#%% Load functions defined in other files
from defs import read_data, create_json


#%%

idf_n = file_path.split('\\')[1].split('.')[0]

# directories
dirs = ['input', 'output']
for i in dirs:
    if not os.path.exists(i):
        os.makedirs(i)


# unicode encoding
enc = 'utf-8'


# INCLUDE REGIONS: True/False
include_regions = False


# SingleLine JSON: True/False
singleLine = False


# list of indictor groups that require an algebraic sign switch
l_as = pd.read_csv('input/algebraic_sign_switch.csv', encoding=enc)
l_as = l_as.indicatorGroup.tolist()


# load line to bar translation table and make dictionary
l2b = pd.read_csv('input/line2bar_combinations.csv', encoding=enc, index_col=0)
dict_l2b = l2b.bar_indicator.to_dict()


# load indicator group to multiplier translation table and make dictionary
i2m = pd.read_csv('input/share_calculation.csv', encoding=enc)

cats = ['region','indicator','indicatorGroup']

#%% Read excel files to a DataFrame

# get list of all input data files with certain file name extension
idf_ex = '.xls'
path_list = glob.glob('input/*' + idf_ex)

# Create an empty DataFrame
data = pd.DataFrame(columns=cats)

# Read files one by one and merge the DataFrames 
for file_path in path_list:
    df = read_data(file_path, enc)
    data = data.append(df, ignore_index=True)

#%%
# check if regions exist, else remove from the category list
if not include_regions:
    del data['region']
    cats.remove('region')


# make auxiliary dataframes
cols = data.columns[data.columns.isin(cats)].tolist()
df1 = data[cols].drop_duplicates().reset_index(drop=True)
df2 = data[['year']].drop_duplicates().reset_index(drop=True)
df3 = data[['scenario']].drop_duplicates().reset_index(drop=True)
df1['total'] = 0
df2['total'] = 0
df3['total'] = 0


# change algebraic sign for selected indicator groups
for i in l_as:
    data.loc[data.indicatorGroup.str.contains(i), 'total'] *= -1


# calculate share per scenario and year
data['multiplier'] = data.indicatorGroup
for i in i2m.sheet_name.unique():
    dict_i2m = i2m[i2m.sheet_name==i].set_index(['indicatorGroup']).multiplier.to_dict()
    data.multiplier.replace(dict_i2m, inplace=True)
data.loc[(data.multiplier.str.isnumeric()==False), 'multiplier'] = 0
data['total_multiplied'] = data.total * data.multiplier

for i in i2m.sheet_name.unique():
    if i in data.chartName:
        data.loc[(data.chartName==i),
                 'total'] = (data[data.chartName==i]\
                             .groupby(['scenario','year'])\
                             .total_multiplied.transform(lambda x: x / x.sum()))


# save meta information
scnNames = data.scenario.unique()


# create min and max values per chart name, title and lable for y axis
data['minY'] = data.total
data.loc[data.minY > 0, 'minY'] = 0
data['maxY'] = data.total
charts = data.groupby(['chartName',
                       'chartTitle',
                       'lable']).agg({'minY':'min','maxY':'max'})
charts = charts.reset_index().to_dict('records')


# create charts text file
with open('output/' + idf_n + 'charts.txt', 'w', encoding=enc) as file:
    text = ''
    for i in charts:
        text += ("<StackedBarChart chartName='" + i['chartName'] +
                 "' chartTitle='" + i['chartTitle'] +
                 "' selectedScenario={selectedScenario} " +
                 "selectedScenario2={selectedScenario2} " +
                 "combinedChart={false} label='" + i['lable'] +
                 "' minY={'" + str(int(i['minY']-.5)) +
                 "'} maxY={'" + str(int(i['maxY']+.5)) + "'} />" + '\n')
    file.write(text)


# create scenarioOptions json file
if include_regions: regNames = data.region.unique()
with open('output/' + idf_n + 'scenarioCombinations.json', 'w',
          encoding=enc) as file:
    text1 = ''
    count1 = 0
    for i in scnNames:
        i = i.replace("_", " ")
        text1 += ("{ \"id\": " + str(count1) +
                 ", \"name\": \"" + i +
                 "\", \"short_description\": \"" + i +
                 "\", \"ultra_short_description\": \"" + '' + "\" }," + '\n')
        count1 += 1
    text2 = ''
    count2 = 0
    if include_regions:
        for i in regNames:
            i = i.replace("_", " ")
            text2 += ("{ \"id\": " + str(count2) +
                     ", \"name\": \"" + i +
                     "\", \"country\": \"" + i +
                     "\", \"short_description\": \"" + i +
                     "\", \"ultra_short_description\": \"" + i + "\" }," +'\n')
            count2 += 1
    text = ("export default {scenarioCombinations : {" +
            "scenarioOptions : [" + '\n' +
            text1[:-2] + '\n' +
            "]," + '\n' +
            "regionOptions : [" + '\n' +
            text2[:-2] + '\n' +
            "]}}")
    file.write(text)


# populate for missing periods
res = pd.merge(df1, df2, on='total')
res = pd.merge(df3, res, on='total')
data = data.append(res, ignore_index=True, sort=True)


# check if regions exist, else remove from the category list
cats = ['scenario',
        'indicator',
        'region',
        'indicatorGroup',
        'year']
if not include_regions: cats.remove('region')


# group by categories and sum the total
data = data.groupby(cats)['total'].sum().reset_index()


if 'line' in idf_n:
    l = data.copy()
    l.indicator.replace(dict_l2b, inplace=True)
else:
    s = data



# create stacked barplot json and save it
if 's' in locals():
    name = 'stackedBar' + idf_n
    create_json(s, cats, name, singleLine, enc)


# create stacked barplot json and save it
if 'l' in locals():
    name = 'line' + idf_n
    create_json(l, cats, name, singleLine, enc)

