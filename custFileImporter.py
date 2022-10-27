import csv
import os.path
import pathlib
import sys

import pandas as pd
import dictCreator
from tkinter import filedialog as fd

dic = pd.read_excel(r'bibliothek/bauform_bibliothek.xlsx')
columnNames = ['R', 'X', 'Y', 'D', 'V', 'T', 'Description']


def main():
    custFileImporter("progFiles/Type1/Air_PFC_Integ_a2/Air_PFC_Integ_a2.mnt")
    for root, dirs, files in os.walk('progFiles/Type1'):
        for fname in files:
            if fname.endswith('.mnb') or fname.endswith('.mnt'):
                path = os.path.join(root, fname)
                print(path)
                bom, res, tmpDic = custFileImporter(path)

    # bom.to_excel("out/processedFileBOM.xlsx")
    # res.to_csv("out/processedFile_real.csv")
    # tmpDic.to_excel("out/tmpDic.xlsx")

    # save updated dictionary
    dic.to_excel("bibliothek/bauform_bibliothek.xlsx")


def custFileImporter(path: str):
    _, ext = os.path.splitext(path)
    if ext == '.mnt' or ext == '.mnb':
        customerFile = importEagle(path)
    elif ext == '.csv':
        customerFile = importCsv(path)
    else:
        sys.exit(f'File type not supported.: {ext}')

    res, tmpDic = translateFile(customerFile)
    bom = createBOM(res)
    return bom, res, tmpDic


def importCsv(path, skipInit: bool = False):
    preprocessCsv(path)
    file = pd.read_csv("in/preprocessed.csv",
                       decimal='.',
                       delim_whitespace=True,
                       index_col=False,
                       header=None,
                       verbose=True,
                       ).fillna('')
    if skipInit:
        mapping = dict(zip(range(7), ['R', 'V', 'T', 'X', 'Y', 'D', 'Description']))
        return file.rename(columns=mapping)
    else:
        return initTable(file, path)


def importXlsx(path, skipInit: bool = False):
    read_file = pd.read_excel(path,
                              index_col=False,
                              header=None)

    # targetPath = pathlib.Path(path)
    # targetPath = targetPath.rename(targetPath.with_suffix('.csv'))
    targetPath = "in/preprocessed.csv"
    read_file.to_csv(targetPath, index=False, header=False, sep=' ')
    return importCsv(targetPath, skipInit)


def importEagle(path, skipInit: bool = False):
    preprocessCsv(path)
    global columnNames
    file = pd.read_csv("in/preprocessed.csv",
                       decimal='.',
                       delim_whitespace=True,
                       index_col=False,
                       verbose=True,
                       header=None
                       ).fillna('')
    return initTable(file, path)


def initTable(df: pd.DataFrame, path: str):
    mapping = dict(zip(range(7), ['R', 'V', 'T', 'X', 'Y', 'D', 'Description']))
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
        print(df.head())
        print("Please specify column order by passing the corresponding column index")
        mapping = dict()
        mapping[6] = "Description"
        for name in ['R', 'V', 'T']:
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
        res = df.rename(columns=mapping)
        print(f"this results in the following mapping:")
        print(mapping)
        if (input("Correct? (y)") in "yY"):
            break
    return res


def preprocessCsv(path):
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
            if (len(line.split(' ')) <= 6):
                line += ' -'
            lines[i] = line
        file.write('\n'.join(lines))


def translateFile(cf: pd.DataFrame):
    mapped = mapFile(cf)
    translated, tmpDic = handleNotTranslated(mapped)
    return translated, tmpDic


def handleNotTranslated(mapped: pd.DataFrame):
    global dic
    tmpDic = pd.DataFrame(columns=['T_source', 'T_target'])
    newEntries = pd.DataFrame(columns=['T_source', 'T_target'])

    noMatch = \
        mapped[mapped.T_target.isnull()][['V', 'T', 'Description']].drop_duplicates().groupby('T', as_index=False).agg(
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
    mapped = mapFile(mapped, pd.concat([tmpDic, dic]))
    return mapped, tmpDic


def mapFile(cf: pd.DataFrame, customDic: pd.DataFrame = dic):
    # global dic
    bauformDictionary = dict(zip(customDic.T_source, customDic.T_target))
    cf["T_target"] = cf['T'].map(bauformDictionary)
    return cf


def createBOM(df: pd.DataFrame):
    bom = df[['R', 'V']].groupby(['V']).agg(list)
    bom["count"] = bom['R'].map(len)
    return bom


if __name__ == "__main__":
    main()
