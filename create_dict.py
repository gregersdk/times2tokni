# -*- coding: utf-8 -*-
"""
Created on Sun May 31 23:42:46 2020

@author: Olex
"""

import pandas as pd
import glob
import os

# %% Set working directory
# Return absolute path to this file
absolute_path = os.path.abspath(__file__)
# Change working directory to this file's directory
os.chdir(os.path.dirname(absolute_path))

# %% Input/output directory settings and more
inputDir = 'input/'
outputDir = inputDir

updateChartMap = True

xlExtension = '.xls'

# Name of the file containing chart overview (chart name, table name, location)
chartMapName = 'dict'

chartMapFields = ['tableName', 'chartName', 'filename']

enc = "utf-8"

"""
possible actions to do with dict file:
    Update existing, e.g. with new tables, keep only tables with data etc.
    Write new, assuming all goes to the first tab
    Clean-up, like update, but also remove those charts without data
"""

# Sheets that do not have a table and should be excluded
excludeSheets = ("Sheet1", "Аркуш1", "Ark1", "Φύλλο1", "Лист1", "Tabelle1")

# %% Create a list with all the table names in the input excel files
# Get a list of all input data files with a given extension
xlFiles = glob.glob(inputDir + '*' + xlExtension)

# Define an empty list that will include all table names
tableNames = list()

# Generate a list of table names found in every excel file and add them to the
# tableNames list
for xlFilePath in xlFiles:

    # Strip file name of its path and extension
    xlFileName = xlFilePath.split('\\')[1].split('.')[0]

    # Read xl file into a dataframe object
    readXlFile = pd.ExcelFile(xlFilePath)

    # Excel sheets
    allXlSheets = readXlFile.sheet_names

    # Return list of sheet names omitting Sheet1, Ark1 and the like
    xlSheets = [x for x in allXlSheets if x not in excludeSheets]

    # Add table names to the list
    for aSheet in xlSheets:
        df = pd.read_excel(readXlFile,
                           sheet_name=aSheet,
                           skiprows=3,
                           encoding=enc,
                           sort=False)
        df = df.dropna(axis=1, how='all')
        tableNames.append(df.iloc[0, 0].split(': ')[1])

# %% Update / generate a new chart map
# Convert tableNames list to a dataframe, avoiding duplicates
df = pd.DataFrame(set(tableNames))

if updateChartMap:

    df.columns = [chartMapFields[0]]

    # Merge table names with an existing chart map
    df = df.merge(pd.read_csv(inputDir + chartMapName + ".csv"), "outer")

    # Fill NaN values in filename with empty string
    df[chartMapFields[2]].fillna("", inplace=True)

    # Fill NaN values in chartName with values from the left (i.e. tableName)
    df.fillna(method="ffill", axis=1, inplace=True)

else:
    # chartName same as tableName
    df[1] = df[0]

    # Default filename
    df[2] = 'stackedBarTab1'

    # Set column names
    df.columns = chartMapFields

df.to_csv(outputDir + chartMapName + '.csv', index=False)
