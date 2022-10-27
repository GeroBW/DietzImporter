import os
import pathlib
import shutil

import pandas as pd
import custFileImporter
import warnings

def main():
    global dic
    extractData('samplefiles_gero', 'progFiles')
    for root, dirs, files in os.walk('progFiles/Type1'):
        for fnameT in files:
            if 'real' in fnameT or 'REAL' in fnameT:
                if fnameT.endswith('.xlsx'):
                    for fnameS in files:
                        if fnameS.endswith('.mnb') or fnameS.endswith('.mnt'):
                            try:
                                src = custFileImporter.importEagle(os.path.join(root, fnameS))
                                trns = custFileImporter.importXlsx(os.path.join(root, fnameT), skipInit=True)
                                createDict(src, trns, pd.read_excel(r'bibliothek/bauform_bibliothek.xlsx'))
                            except:
                                warnings.warn(f"Skipped src {fnameS} with trns {fnameT} in {root}")
                                continue
            if fnameT == files[-1]:
                path = os.path.join("out", 'processedProjects/', pathlib.PurePath(root).name)
                shutil.copytree(root, path, dirs_exist_ok=True)
                shutil.rmtree(root)


def extractData(src: str, dest: str):
    shutil.rmtree(dest)
    dirAcc = set()
    for root, dirs, files in os.walk(src):
        for name in files:
            if 'real' in name:
                dirAcc.add(root)
    dirType1 = set([dir for dir in dirAcc if isType1(dir)])
    dirRest = dirAcc - dirType1
    for directory in dirType1:
        path = os.path.join(dest, 'Type1/', pathlib.PurePath(directory).parent.name)
        if not os.path.exists(path): shutil.copytree(directory, path, dirs_exist_ok=False)
    for directory in dirRest:
        path = os.path.join(dest, 'Rest/', pathlib.PurePath(directory).parent.name)
        if not os.path.exists(path): shutil.copytree(directory, path, dirs_exist_ok=False)


def isType1(dir):
    files = os.listdir(dir)
    return ((1 == sum(fname.endswith('.mnt') for fname in files)
             or 1 == sum(fname.endswith('.mnb') for fname in files))
            and any(fname.endswith('.brd') for fname in files))


def createDict(src: pd.DataFrame, trns: pd.DataFrame, dictionaryOld: pd.DataFrame):
    matched = pd.merge(left=src[['R', 'V', 'T', 'Description']], right=trns[['R', 'V', 'T', 'Description']], on=['R']).drop_duplicates(subset=['T_x', 'T_y'])
    duplicates = matched[matched.duplicated(subset=['T_x'], keep=False)]
    while len(duplicates) > 0:
        print("Found duplicate in this projects translations.")
        key = duplicates['T_x'].unique()[0]
        thisDupl = duplicates[duplicates['T_x'] == key]
        print(thisDupl)
        try:
            userInput = input("""
        Which one would you like to keep?
        Please enter row Index (first column) or delete all (d).
        """, )
            if(userInput in "d"):
                print("deleting all")

            index = int(userInput)
            if index in thisDupl.index:
                print("deleting row:", index)
                matched = matched.drop([index])
            else:
                print(index, " is not a valid index")
        except:
            print(f"{userInput}Is not an int or 'd'!")

        duplicates = matched[matched.duplicated(subset=['T_x'], keep=False)]

    ### saving file
    dictNewLines = matched.rename(columns={'T_x': 'T_source', 'T_y': 'T_target'})[['T_source', 'T_target']]
    dictionaryNew = pd.concat([dictionaryOld, dictNewLines]).drop_duplicates()

    print("Saving the following file\n:", dictionaryNew)
    dictionaryNew[['T_source', 'T_target']].to_excel('bibliothek/bauform_bibliothek.xlsx', index=False)


if __name__ == "__main__":
    main()
