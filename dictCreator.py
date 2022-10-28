import os
import pathlib
import shutil

import pandas as pd
import custFileImporter
import warnings

if os.path.exists(r'bibliothek/bauform_bibliothek.xlsx'):
    dic = pd.read_excel(r'bibliothek/bauform_bibliothek.xlsx')
else:
    dic = pd.DataFrame(columns=["T_source","T_target", "R_type"])
    dic.to_excel(r'bibliothek/bauform_bibliothek.xlsx', index=False)
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
                                src = custFileImporter.importEagle(os.path.join(root, fnameS), skipInit=True)
                                trns = custFileImporter.importXlsx(os.path.join(root, fnameT), skipInit=True)
                                createDict(src, trns, pd.read_excel(r'bibliothek/bauform_bibliothek.xlsx'))
                            except:
                                warnings.warn(f"Skipped src {fnameS} with trns {fnameT} in {root}")
                                continue
            if fnameT == files[-1]:
                path = os.path.join("out", 'processedProjects/', pathlib.PurePath(root).name)
                shutil.copytree(root, path, dirs_exist_ok=True)
                # shutil.rmtree(root)


def extractData(src: str, dest: str):
    # shutil.rmtree(dest)
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
    matched = pd.merge(left=src[['R', 'V', 'T', 'Description']], right=trns[['R', 'T', 'Description']],
                       on=['R']).drop_duplicates(subset=['T_x', 'T_y'])
    matched = matched.rename(columns={'T_x': 'T_source', 'T_y': 'T_target'})
    matched = matched[matched.apply(lambda x: "n.b." not in x['T_target'] and "hand" not in x['T_target'] and "Hand" not in x['T_target'], axis = 1)]
    matched["R_type"] = matched['R'].str.replace('\d+', '').apply(lambda x: x if x == 'C' or x =='R' else '')
    matched = removeConflicts(matched)[['R_type','T_source', 'T_target']]
    newlines = matched[['R_type','T_source', 'T_target']]
    ### saving file
    dictionaryNew = pd.concat([dictionaryOld, newlines]).drop_duplicates()
    dictionaryNew = removeConflicts(dictionaryNew)

    print("Saving the following file\n:", dictionaryNew)
    dictionaryNew.to_excel('bibliothek/bauform_bibliothek.xlsx', index=False)


def removeConflicts(matched):
    duplicates = matched[matched.duplicated(subset=['T_source','R_type'], keep=False)]
    while len(duplicates) > 0:
        print("Found duplicate in this projects translations.")
        key = duplicates['T_source'].unique()[0]
        thisDupl = duplicates[duplicates['T_source'] == key]
        print(thisDupl)
        # userInput = input("""
        # Which one would you like to keep?
        # Please enter row Index (first column) or delete all (d).
        # """, )
        userInput = 'd'
        if (userInput in "d"):
            print("deleting all")
            matched = matched.drop(list(thisDupl.index))
        else:
            try:
                index = int(userInput)
                if index in thisDupl.index:
                    print("deleting row:", index)
                    matched = matched.drop([index])
                else:
                    print(index, " is not a valid index")
            except:
                print(f"{userInput}Is not an int or 'd'!")
        duplicates = matched[matched.duplicated(subset=['T_source','R_type'], keep=False)]
    return matched

if __name__ == "__main__":
    main()
