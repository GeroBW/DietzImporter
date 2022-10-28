import csv
import os.path
import pathlib
import sys

import pandas
import pandas as pd
import dictCreator
from tkinter import filedialog as fd

pandas.set_option('display.max_columns', None)

dic = pd.read_excel(r'bibliothek/bauform_bibliothek.xlsx')
columnNames = ['R', 'X', 'Y', 'D', 'V', 'T', 'Description']


def main():
    for root, dirs, files in os.walk('in'):
        for fname in files:
            path = os.path.join(root, fname)
            print(f'importing {path}')
            bom, res, tmpDic = custFileImporter(path)

            basename, ext = os.path.splitext(path)
            basename = os.path.basename(os.path.normpath(basename))
            if not os.path.exists(f'out/{basename}'):
                os.mkdir(f'out/{basename}')
            if not os.path.exists(f'bibliothek/{basename}'):
                os.mkdir(f'bibliothek/{basename}')

            bom.to_excel(f"out/{basename}/{basename}_real_BOM.xlsx")
            res.to_csv(f"out/{basename}/{basename}_real.csv")
            tmpDic.to_excel(
                f"bibliothek/{basename}/{basename}_tmpDic.xlsx")

    # save updated dictionary
    dic.to_excel("bibliothek/bauform_bibliothek.xlsx")


def custFileImporter(path: str):
    _, ext = os.path.splitext(path)
    if ext == '.mnt' or ext == '.mnb':
        customerFile = importEagle(path)
    elif ext == '.csv':
        customerFile = importCsv(path)
    elif ext == '.xlsx':
        customerFile = importXlsx(path)
    else:
        sys.exit(f'File type not supported.: {ext}')

    res, tmpDic = translateFile(customerFile)
    bom = createBOM(res)
    return bom, res, tmpDic


def importCsv(path, skipInit: bool = False):
    # preprocessCsv(path)
    file = pd.read_csv(path,
                       decimal='.',
                       # delim_whitespace=True,
                       index_col=False,
                       header=None,
                       verbose=True,
                       ).fillna('')
    file = file.apply(lambda x: x.str.replace(',','.'))
    if skipInit:
        mapping = dict(zip(range(7), columnGuesser(file)))
        return file.rename(columns=mapping)
    else:
        return initTable(file, path, columnGuess=columnGuesser(file))


def importXlsx(path, skipInit: bool = False):
    read_file = pd.read_excel(path,
                              index_col=False,
                              header=None)

    # targetPath = pathlib.Path(path)
    # targetPath = targetPath.rename(targetPath.with_suffix('.csv'))
    targetPath = "in/preprocessed.csv"
    read_file.to_csv(targetPath, index=False, header=False, sep=',')
    return importCsv(targetPath, skipInit)


def importEagle(path, skipInit: bool = False):
    preprocessEagle(path)
    global columnNames
    file = pd.read_csv("in/preprocessed.csv",
                       decimal='.',
                       delim_whitespace=True,
                       index_col=False,
                       verbose=True,
                       header=None
                       ).fillna('')
    if skipInit:
        mapping = dict(zip(range(7), columnGuesser(file)))
        return file.rename(columns=mapping)
    else:
        return initTable(file, path, columnGuess=columnGuesser(file))


def columnGuesser(df: pd.DataFrame):
    numberColumns = ["X", "Y", "D"]
    otherColumns = ["R", "V", "T", "Description"]
    columnGuess = []
    try:
        for type in df.dtypes:
            if type.kind in 'iufc':
                columnGuess.append(numberColumns.pop(0))
            else:
                columnGuess.append(otherColumns.pop(0))
        return columnGuess
    except:
        return None


def initTable(df: pd.DataFrame, path: str, columnGuess: list = None):
    res = df
    if columnGuess:
        mapping = dict(zip(range(7), columnGuess))
        res = df.rename(columns=mapping)

    print(res.head())
    userInput = input(
    "Are the Column Names and first Rows correct? y, 1: drop first row, 2: edit columns, 3: Do both (1 and 2)")
    if userInput in "yY":
        return res
    if userInput == "1":
        return res.iloc[1:]
    if userInput == "3":
        res = res.iloc[1:]

    print(f"initializing column names for {path}")
    while True:
        print(res.head())
        print("Please specify column order by passing the corresponding column index")
        mapping = dict()
        for name in ['R', 'V', 'T', "Description"]:
            while True:
                try:
                    userInput = int(input(f"{name}:"))
                except:
                    print("That's not an int!")
                    continue
                if userInput not in mapping.keys():
                    mapping[userInput] = name
                    break
                else:
                    print(f"column already assigned to {mapping[userInput]}")
        res = res.rename(columns=mapping)
        print(f"this results in the following mapping:")
        print(mapping)
        if (input("Correct? (y)") in "yY"):
            break
    return res


def preprocessEagle(path):
    data = ""
    ##todo ignore non data columns
    with open(path, encoding="ISO-8859-1", ) as file:
        data = file.read() \
            .replace(",", ".") \
            .replace("µ", "u")
    with open("in/preprocessed.csv", "w+") as file:
        lines = data.splitlines()
        for i, line in enumerate(lines):
            line = ' '.join(line.split())
            line = (' '.join(line.split(' ')[:6]) + ' ' + '_'.join(line.split(' ')[6:])).strip()
            if (len(line.split(' ')) <= 7):
                line += ' -'
            lines[i] = line
        file.write('\n'.join(lines))


def translateFile(cf: pd.DataFrame):
    mapped = mapFile(cf)
    translated, tmpDic = handleNotTranslated(mapped)
    return translated, tmpDic


def handleNotTranslated(translated: pd.DataFrame):
    global dic
    tmpDic = pd.DataFrame(columns=['T_source', 'T_target'])
    newEntries = pd.DataFrame(columns=['T_source', 'T_target'])

    noMatch = \
        translated[translated.T_target.isnull()][['V', 'T', 'Description']].drop_duplicates().groupby('T',
                                                                                                      as_index=False).agg(
            list)[['V', 'T', 'Description']]
    noMatch["Description"] = noMatch["Description"].map(lambda x: ', '.join(set(x)))
    print("No translation found for the following parts:")
    print(noMatch.to_string(index=False))
    q = input('Start translation in program? (y)\n Alternatively, you can expand the bauform_bibliothek.xlsx\n')
    # q = 'n'
    if 'y' == q or 'Y' == q:
        for i in noMatch.index:
            notTrans = noMatch.loc[[i]]
            print(notTrans.to_string(index=False))
            q = input(
                f"Choose option:\n\t1: Always translate this Part\n\t2: Translate for this file only\n\t3: skip this part\n\tq: save and exit translation mode\n")
            if q == '1' or q == '2':
                while True:
                    targetType = input(f"Enter correct part Name:")
                    yorN = input(f"entered '{targetType}'. Is this correct? (y)")
                    if yorN == 'y' or yorN == 'Y':
                        if q == '1':
                            print(f"adding {notTrans['T']} -> {targetType} to dictionary.")
                            new_row = pd.DataFrame(data={"T_source": notTrans['T'], 'T_target': targetType})
                            newEntries = pd.concat([newEntries, new_row])
                        if q == '2':
                            new_row = pd.DataFrame(data={"T_source": notTrans['T'], 'T_target': targetType})
                            tmpDic = pd.concat([tmpDic, new_row])
                        break
            if q == '3':
                print('Skipping part')
            if q == 'q':
                break
    dic = pd.concat([dic, newEntries])
    translated = mapFile(translated, pd.concat([tmpDic, dic]))
    return translated, tmpDic


def mapFile(cf: pd.DataFrame, customDic: pd.DataFrame = dic):
    # global dic
    bauformDictionary = dict(zip(customDic.T_source, customDic.T_target))
    t_target = cf['T'].map(bauformDictionary)
    if 'T_target' in cf.columns:
        cf['T_target'] = t_target
    else:
        cf.insert(cf.columns.get_loc("T"), "T_target", t_target)
    return cf


def createBOM(df: pd.DataFrame):
    bom = df[['R', 'V']].groupby(['V']).agg(list)
    bom["count"] = bom['R'].map(len)
    return bom


if __name__ == "__main__":
    main()
