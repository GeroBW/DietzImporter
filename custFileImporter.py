import csv
import os.path
import pathlib
import sys
import warnings

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
            _, ext = os.path.splitext(path)
            if ext in ['.mnt', '.mnb', '.csv', '.txt', '.xlsx']:
                print(f'importing {path}')
                bom, res, tmpDic = custFileImporter(path)

                basename, ext = os.path.splitext(path)
                basename = os.path.basename(os.path.normpath(basename))
                if not os.path.exists(f'out/{basename}'):
                    os.mkdir(f'out/{basename}')
                if not os.path.exists(f'bibliothek/{basename}'):
                    os.mkdir(f'bibliothek/{basename}')
                bom.to_excel(f"out/{basename}/{basename}_{ext}_real_BOM.xlsx")
                # res.to_csv(f"out/{basename}/{basename}_{ext}_real.csv", index=False)
                res.drop(['R_type'], axis=1).rename(columns={'T': 'T_old', 'T_target': 'T'}).to_excel(
                    f"out/{basename}/{basename}_{ext}_real.xlsx", index=False)
                #
                # tmpDic.to_excel(
                #     f"bibliothek/{basename}/{basename}_{ext}_tmpDic.xlsx")
            else:
                print(f'File type not supported.: {ext}')

    # save updated dictionary
    dic.to_excel("bibliothek/bauform_bibliothek.xlsx", index=None)


def custFileImporter(path: str):
    _, ext = os.path.splitext(path)
    if ext == '.mnt' or ext == '.mnb':
        customerFile = importEagle(path)
    elif ext == '.csv' or ext == '.txt':
        customerFile = importCsv(path)
    elif ext == '.xlsx':
        customerFile = importXlsx(path)
    else:
        sys.exit(f'File type not supported.: {ext}')

    res, tmpDic = translateFile(customerFile)
    bom = createBOM(res)
    return bom, res, tmpDic


def importCsv(src, skipInit: bool = False):
    tmp = "pre/preprocessed.csv"
    userInput = input("Are the CSV seperators whitespaces? y")
    delimWhite = userInput in 'yY'
    delimiter = None
    if not delimWhite:
        delimiter = input("Please enter delimiter")
    file = pd.read_csv(src,
                       decimal='.',
                       delim_whitespace=delimWhite,
                       index_col=False,
                       header=None,
                       verbose=True,
                       delimiter=delimiter
                       ).fillna('')
    file.to_csv(tmp, sep=' ')
    replaceMu(tmp, tmp)
    concatExcessColumns(tmp, tmp)
    file = pd.read_csv(tmp,
                       decimal='.',
                       delim_whitespace=True,
                       index_col=False,
                       header=None,
                       verbose=True,
                       ).fillna('')
    # file = file.apply(lambda x: x.str.replace(',','.'))

    if skipInit:
        mapping = dict(zip(range(7), columnGuesser(file)))
        return file.rename(columns=mapping)
    else:
        return initTable(file, src, columnGuess=columnGuesser(file))


def importXlsx(path, skipInit: bool = False):
    read_file = pd.read_excel(path,
                              index_col=False,
                              header=None)

    # targetPath = pathlib.Path(path)
    # targetPath = targetPath.rename(targetPath.with_suffix('.csv'))
    targetPath = "pre/preprocessed.csv"
    read_file.to_csv(targetPath, index=False, header=False, sep=' ')
    preprocessEagle(targetPath)
    file = pd.read_csv("pre/preprocessed.csv",
                       decimal='.',
                       delim_whitespace=True,
                       index_col=False,
                       header=None,
                       verbose=True,
                       ).fillna('')
    if skipInit:
        mapping = dict(zip(range(7), columnGuesser(file)))
        return file.rename(columns=mapping)
    else:
        return initTable(file, path, columnGuess=columnGuesser(file))


def importEagle(path, skipInit: bool = False):
    preprocessEagle(path)
    global columnNames
    file = pd.read_csv("pre/preprocessed.csv",
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


def initTable(df: pd.DataFrame, src: str, columnGuess: list = None):
    res = df
    if columnGuess:
        mapping = dict(zip(range(7), columnGuess))
        res = df.rename(columns=mapping)

    print(res.head())
    userInput = input(
        "y: Columns are correct, e: edit columns, a: abort")
    if userInput in "yY":
        return res
    # "1: drop first row, "
    # if userInput == "1":
    #     return res.iloc[1:]
    # "3: Do both (1 and 2)"
    # if userInput == "3": df = df.iloc[1:]
    if userInput in "aA":
        exit("Process aborted")
    res = df

    print("Please specify columns that should be deleted by passing the corresponding column index")
    while True:
        print(res.head())
        userInput = input("Delete column (i), done(d), abort:")
        if userInput == "a":
            exit("Process aborted")

        if userInput in "dD":
            break
        else:
            try:
                userInput = int(userInput)
                if userInput in res.columns:
                    if (input(f"Confirm deleting column {userInput} (y)") in "yY"):
                        res = res.drop(userInput, axis=1)

            except:
                print("invalid entry")
                continue

    targetPath = "pre/preprocessed.csv"
    res.to_csv(targetPath, index=False, header=False, sep=' ')
    concatExcessColumns(targetPath, targetPath)
    res = pd.read_csv(targetPath,
                      decimal='.',
                      delim_whitespace=True,
                      index_col=False,
                      header=None,
                      verbose=True,
                      ).fillna('')

    while True:
        print(res.head())
        print("Please specify column order by passing the corresponding column index, abort: a")
        mapping = dict()
        for name in ['R', 'V', 'T', "Description"]:
            while True:
                userInput = input(f"{name}:")
                if userInput == "a": exit("Process aborted")
                try:
                    userInput = int(userInput)
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
        userInput = input("Correct? (y), abort: a")
        if userInput == "a": exit("Process aborted")
        if (userInput in "yY"): break
    return res


def preprocessEagle(path):
    data = ""
    ##todo ignore non data columns
    with open(path, encoding="ISO-8859-1", ) as file:
        data = file.read() \
            .replace(",", ".") \
            .replace("µ", "u")
    with open("pre/preprocessed.csv", "w+") as file:
        lines = data.splitlines()
        for i, line in enumerate(lines):
            line = ' '.join(line.split())
            line = (' '.join(line.split(' ')[:6]) + ' ' + '_'.join(line.split(' ')[6:])).strip()
            if (len(line.split(' ')) <= 6):
                line += ' -'
            lines[i] = line
        file.write('\n'.join(lines))


def replaceMu(src, dest):
    data = ""
    ##todo ignore non data columns
    with open(src, encoding="ISO-8859-1", ) as file:
        data = file.read() \
            .replace(",", ".") \
            .replace("µ", "u")
    with open(dest, "w+") as file:
        file.write(data)
    return dest


def concatExcessColumns(path, dest):
    with open(path, encoding="ISO-8859-1", ) as file:
        data = file.read()
    with open(dest, "w+") as file:
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


def handleNotTranslated(translated: pd.DataFrame):
    global dic
    tmpDic = pd.DataFrame(columns=['T_source', 'T_target'])
    newEntries = pd.DataFrame(columns=['T_source', 'T_target'])

    noMatch = \
        translated[translated.T_target.isnull()][['V', 'T', 'Description']].drop_duplicates().groupby('T',
                                                                                                      as_index=False).agg(
            list)[['V', 'T', 'Description']]
    noMatch["Description"] = noMatch["Description"].map(lambda x: ', '.join(set(x)))
    if not len(noMatch.index):
        print("All parts where translated successfully.")
        return translated, tmpDic
    print("No translation found for the following parts:")
    print(noMatch.to_string(index=False))
    q = input('Start translation in program? (y)\n Alternatively, you can expand the bauform_bibliothek.xlsx (enter)\n')
    if 'y' == q or 'Y' == q:
        for i in noMatch.index:
            notTrans = noMatch.loc[[i]]
            print(notTrans.to_string(index=False))
            q = input(
                f"Choose option:\n\t1: Always translate this Part\n\t2: Translate for this file only\n\t3: skip this part\n\tq: save and exit translation mode, a: abort\n")
            if q == "a": exit("Process aborted")
            if q == 'q': break
            if q == '1' or q == '2':
                while True:
                    targetType = input(f"Enter correct part Name:")
                    yorN = input(f"entered '{targetType}'. Is this correct? (y)")
                    if yorN in 'yY':
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
    dic = pd.concat([dic, newEntries])
    translated = mapFile(translated, pd.concat([tmpDic, dic]))
    return translated, tmpDic


def mapFile(cf: pd.DataFrame, customDic: pd.DataFrame = dic):
    global dic
    cf['R_type'] = cf['R'].str.replace(r'\d+', '', regex=True).apply(lambda x: x if x == 'C' or x == 'R' else '')
    t_target = cf.apply(joinRow, axis=1, result_type='reduce')
    if 'T_target' in cf.columns:
        cf['T_target'] = t_target
    else:
        cf.insert(cf.columns.get_loc("T") + 1, "T_target", t_target)
    return cf


def joinRow(row):
    matched_parts = dic[dic['T_source'] == str(row['T'])]
    if len(matched_parts) == 0: return None
    if len(matched_parts) == 1: return matched_parts['T_target'].item()
    if row['R_type']:
        res = matched_parts[matched_parts['R_type'] == row['R_type']]
        if len(res) == 1:
            return res['T_target'].item()
        else:
            print("found conflicts:")
            print(matched_parts)
    return None


def createBOM(df: pd.DataFrame):
    bom = df[['R', 'V']].groupby(['V']).agg(list)
    bom["count"] = bom['R'].map(len)
    return bom


if __name__ == "__main__":
    main()
