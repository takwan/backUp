#!/ccnc_bin/venv/bin/python -> D1: ananconda
# -*- coding: utf-8 -*-
'''
# Back up data and forms a database from the MRI data
# Created by Kang Ik Kevin Cho
# Contributors: Dahye Stella Bae, Eunseo Cho
# python backUp.py -x -m      (If: changed paths correctly)
'''
from __future__ import division
import re
import time
from datetime import date
import sys
import os
from os.path import join, basename, dirname, isdir
import shutil
from progressbar import AnimatedMarker, ProgressBar, Percentage, Bar
import argparse
import textwrap
import pandas as pd
import updateSpreadSheet
#import motionExtraction
#import easyFreesurfer #bienseo: not work -> using freesurfer.py
#import freesurfer_Summary # bienseo: not work
import subject as subj
#import dtifit as bien #bienseo dti fa map

# scp modules for network dual back up
#import getpass
#from paramiko import SSHClient
#from scp import SCPClient


def backUp(inputDirs, backUpTo,
           DataBaseAddress, spreadsheet):

    subjectClassList = []
    for newDirectory in inputDirs:
        subjClass = subj.subject(newDirectory, backUpTo)
        checkFileNumbers(subjClass)
        subjectClassList.append(subjClass)

        executeCopy(subjClass)

        subjDf = saveLog(subjClass)

        dbDf = processDB(DataBaseAddress)

        newDf = pd.concat([dbDf, subjDf]).reset_index()
        newDf = newDf[[ u'koreanName',  
                        u'subjectName',
                        u'subjectInitial',
                        u'group',
                        u'sex',
                        u'age',
                        u'DOB',
                        u'scanDate',
                        u'timeline',
                        u'studyname',
                        u'patientNumber',
                        u'T1',
                        u'T2',
                        u'REST_LR',
                        u'REST_LR_SBRef',
                        u'REST_BLIP_LR',
                        u'REST_BLIP_RL',
                        u'DTI_LR_1000',
                        u'DTI_LR_2000',
                        u'DTI_LR_3000',
                        u'DTI_BLIP_LR',
                        u'DTI_BLIP_RL',
                        u'dx',
                        u'folderName',
                        u'backUpBy',
                        u'note']]
        #please confirm here

        newDf['koreanName'] = newDf['koreanName'].str.decode('utf-8')
        newDf['note'] = newDf['note'].str.decode('utf-8')
        newDf.to_excel(DataBaseAddress, 'Sheet1')
        # os.chmod(DataBaseAddress, 0o2770)

        updateSpreadSheet.main(False, DataBaseAddress, spreadsheet)#False
    print('Completed\n')

def noCall(logDf, backUpFrom, folderName):
    logDf = pd.concat([logDf,pd.DataFrame.from_dict({'directoryName': folderName,
                                                     'backedUpBy': getpass.getuser(),
                                                     'backedUpAt': time.ctime()},orient='index').T])
    return logDf


def copiedDirectoryCheck(backUpFrom, logFileInUSB):
    if os.path.isfile(logFileInUSB):
        df = pd.read_excel(logFileInUSB,'Sheet1')
        print('Log loaded successfully')
    else:
        df = pd.DataFrame.from_dict({
                                     'directoryName': None,
                                     'backedUpBy': None,
                                     'backedUpAt': None
                                    },orient='index').T
    return df


def findNewDirs(backUpFrom, logDf):
    '''
    List the new directories under the back up source dir,
    and get confirm from the user.
    '''
    toBackUp = []

    # grebbing directories in the target
    allFiles = os.listdir(backUpFrom)
    directories = [item for item in allFiles if isdir(join(backUpFrom, item))
                   and not item.startswith('$')
                   and not item.startswith('.')]

    newDirectories = [item for item in directories if not item in [str(x).encode("ascii") for x in logDf.directoryName]]

    for folderName in newDirectories:
        subjFolder = os.path.join(backUpFrom, folderName)
        stat = os.stat(subjFolder)
        created = os.stat(subjFolder).st_ctime
        asciiTime = time.asctime(time.gmtime(created))
        print('''
        ------------------------------------
        ------{0}
        created on ( {1} )
        ------------------------------------
        '''.format(folderName,asciiTime))
        response = input('\nIs this the name of the subject you want to back up?'
                             '[Yes/No/Quit/noCall] : ')

        if re.search('[yY]|[yY][Ee][Ss]',response):
            toBackUp.append(subjFolder)
        elif re.search('[Dd][Oo][Nn][Ee]|stop|[Qq][Uu][Ii][Tt]|exit',response):
            break
        elif re.search('[Nn][Oo][Cc][Aa][Ll][Ll]',response):
            logDf = noCall(logDf, backUpFrom, folderName)
        else:
            continue

    print(toBackUp)
    return toBackUp, logDf


def calculate_age(born, today):
    try:
        birthday = born.replace(year=today.year)
    except ValueError: # raised when birth date is February 29 and the current year is not a leap year
        birthday = born.replace(year=today.year, day=born.day-1)
    if birthday > today:
        return today.year - born.year - 1
    else:
        return today.year - born.year


def checkFileNumbers(subjClass):
    # Make a checking list
    checkList = {
                 'T1': 224,
				 'T2': 224,
				 'REST_LR': 250,
				 'REST_LR_SBRef': 1,
				 'REST_BLIP_LR': 3,
				 'REST_BLIP_RL': 3,
				 'DTI_LR_1000': 21,
				 'DTI_LR_2000': 31,
				 'DTI_LR_3000': 65,
				 'DTI_BLIP_LR': 7,
				 'DTI_BLIP_RL': 7,
                 'SCOUT': 9
                }

    # Check whether they have right numbers
    for modality, (modalityLocation, fileCount) in zip(subjClass.modalityMapping, subjClass.dirDicomNum):
        if checkList[modality] != fileCount:
            print('{modality} numbers does not seem right !  : {fileCount}'.format(
                    modality=modality,
                    fileCount=fileCount))
            if re.search('[yY]|[yY][Ee][Ss]',input('\tCheck ? [ Y / N ] : ')):
                print('\tOkay !')
            else:
                print('\tExit due to unmatching file number')
                sys.exit(0)
        else:
            print('Correct dicom number - \t {modality} : {fileCount}'.format(
                   modality=modality,
                   fileCount=fileCount))


def executeCopy(subjClass):
    print('-----------------')
    print('Copying', subjClass.koreanName)
    print('-----------------')

    totalNum = subjClass.allDicomNum
    accNum = 0
    pbar = ProgressBar().start()
    for source, modality, num in zip(subjClass.dirs, 
                                     subjClass.modalityMapping, 
                                     subjClass.modalityDicomNum.values()):

        os.system('mkdir -p {0}'.format(subjClass.targetDir))

        modalityTarget = os.path.join(subjClass.targetDir, modality)
        shutil.copytree(source, modalityTarget)
        accNum += num
        pbar.update((accNum/totalNum) * 100)
    pbar.finish()


def processDB(DataBaseAddress):
    if os.path.isfile(DataBaseAddress):
        excelFile = pd.ExcelFile(DataBaseAddress)
        df = excelFile.parse(excelFile.sheet_names[0])
        df['koreanName'] = df.koreanName.str.encode('utf-8')
        df['note'] = df.note.str.encode('utf-8')

        print('df in processDf first parag')
        print(df)

    else:
        df = pd.DataFrame.from_dict({ None: {
                                               'subjectName': None,
                                               'subjectInitial': None,
                                               'group': None,
                                               'sex': None,
                                               'DOB': None,
                                               'scanDate': None,
                                               'age': None,
                                               'timeline': None,
                                               'studyname': None,
                                               'folderName': None,
                                               'T1Number': None,
                                               'DTINumber': None,
                                               'DKINumber': None,
                                               'RESTNumber': None,
                                               'note': None,
                                               'patientNumber': None,
                                               'folderName': None,
                                               'backUpBy': None
                                            }
                                     },orient='index'
                                    )
    return df

def saveLog(sub):
    df = makeLog(sub.koreanName, sub.group, sub.timeline, sub.dob, sub.note,
                 sub.initial, sub.fullname, sub.sex, sub.id, sub.study,
                 sub.date, sub.folderName, sub.modalityDicomNum, sub.experimenter)
    df.to_csv(os.path.join(sub.targetDir, 'log.txt'))
    return df

def makeLog(koreanName, group, timeline, dob, note,
            subjInitial, fullname, sex, subjNum, studyname,
            scanDate, folderName, modalityCount, user):

    dateOfBirth = date(int(dob[:4]), int(dob[4:6]), int(dob[6:]))
    formalSourceDate = date(int(scanDate[:4]),int(scanDate[4:6]), int(scanDate[6:]))
    age = calculate_age(dateOfBirth,formalSourceDate)

    # Image numbers
    images = ['T1','DTI','DKI','REST','T2FLAIR','T2TSE','REST2']
    imageNumbers = {}
    for image in images:
        try:
            imageNumbers[image] = modalityCount[image]
        except:
            imageNumbers[image] = ''

    # New dictionary  
    allInfoRearranged = {}
    allInfoRearranged = {
                            'koreanName': koreanName,
                            'subjectName': fullname,
                            'subjectInitial': subjInitial,
                            'group': group,
                            'sex': sex,
                            'timeline': timeline,
                            'studyname': studyname,
                            'DOB': dateOfBirth.isoformat(),
                            'scanDate': formalSourceDate.isoformat(),
                            'age': age,

                            'note': note,
                            'patientNumber': subjNum,
                            'folderName': folderName,
                            'backUpBy': user,
                            
                            'T1Number': imageNumbers['T1'],
                            'DTINumber': imageNumbers['DTI'],
                            'DKINumber': imageNumbers['DKI'],
                            'RESTNumber': imageNumbers['REST'],
                            'REST2Number': imageNumbers['REST2'] 
                        }
    allInfoDf = pd.DataFrame.from_dict(allInfoRearranged,orient='index').T
    allInfoDf = allInfoDf[[ 
                            u'koreanName',  u'subjectName',   u'subjectInitial',
                            u'group',       u'sex',           u'age',
                            u'DOB',         u'scanDate',      u'timeline',
                            u'studyname',   u'patientNumber', u'T1Number',
                            u'DTINumber',   u'DKINumber',     u'RESTNumber',
                            u'REST2Number', u'folderName',    u'backUpBy',
                            u'note'
                         ]]
    return allInfoDf


def server_connect(server, data_from):
    ssh = SSHClient()
    ssh.load_system_host_keys()
    username = 'admin'
    data_to = '/volume1/dual_back_up'
    password = getpass.getpass('Password admin@nas : ')
    ssh.connect(server, username=username, password=password)

    with SCPClient(ssh.get_transport()) as scp:
        print('Connected to {server} and copying data'.format(server=server))
        print('\t',data_from,'to',server+'@'+data_to)
        scp.put(data_from, data_to, recursive=True, preserve_times=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=textwrap.dedent('''\
            {codeName} : Copy MRI data from external hard drive to system.
                         It automatically adds logs to ccnc database.
            ========================================
            eg) {codeName}
            '''.format(codeName=basename(__file__))))

    parser.add_argument(
        '-i', '--inputDirs',
        help='One or more locations of data to back up. Eg) /Volumes/20160420/CHO_KANG_IK_12344321',
        nargs='*',
        default=False, )

    parser.add_argument(
        '-h', '--hddDir',
        help='Location of external drive to search for new data. Eg) /Volumes/20160420',
        default='/media/MRI_cohort',) 

    parser.add_argument(
        '-b', '--backupDir',
        help='Location of data storage root. Default : "/volumes/CCNC_MRI/CCNC_MRI_3T"',
        default='/volume/CCNC_MRI/BCS_MRI',)

    parser.add_argument(
        '-d', '--database',
        help='Location of database file. Default : "/volumes/CCNC_MRI/CCNC_MRI_3T/database/database.xls"',
        default='/volume/CCNC_MRI/BCS_MRI/database/database_bcs.xlsx',) 

    parser.add_argument(
        '-s', '--spreadsheet',
        help='Location of output excel file. Default : "/ccnc/MRIspreadsheet/MRI.xls"',
        default="/volume/CCNC_MRI/BCS_MRI/MRI.xls",) #change this later TW

    parser.add_argument(
        '-f', '--freesurfer',
        help='Run freesurfer',
        action='store_true',
        default=False,)

    parser.add_argument(
        '-m', '--motion',
        help='Run motion extraction',
        action='store_true',
        default=False,)

    parser.add_argument(
        '-n', '--nasBackup',
        help='Makes dual back up to NAS',
        action='store_true',
        default=False,
        )
    args = parser.parse_args()

    # Run backUp
    if args.inputDirs: # if input directories are specified
        backUp(args.inputDirs, 
               args.backupDir, 
               args.database, args.spreadsheet)
    else: # search external HDD
        log_file_in_hdd = join(args.backUpFrom,"log.xlsx")
        log_df = copiedDirectoryCheck(args.backUpFrom,
                                     log_file_in_hdd)
        inputDirs, log_df_updated = findNewDirs(backUpFrom,
                                                log_df)
        log_df_updated.to_excel(log_file_in_hdd,'Sheet1')
        if inputDirs == []:
            sys.exit('Everything have been backed up !')

        backUp(inputDirs, 
               args.backupDir, 
               args.database, args.spreadsheet)

    # Run motion check
    #args.motion
    #if motion:
        #print 'Now, running motion_extraction'
        #for subjectClass in subjectClassList:
            #motionExtraction.main(subjectClass.targetDir, True, True, False)
            #bien.dtiFit(os.path.join(subjectClass.targetDir,'DTI'))

    # Run freesurfer
    #args.freesurfer
   # freesurfer.py import error #bienseo
   # if freesurfer:
   #     for subjectClass in subjectClassList:
   #         easyFreesurfer.main(subjectClass.targetDir, 
   #                             os.path.join(subjectClass.targetDir,'FREESURFER'))
   #         freesurfer_Summary.main(copiedDir, None,                #bienseo: only use freesurfer.
   #                                 "ctx_lh_G_cuneus", True, True, True, True)

    # Run nas backup
    #args.nasBackup
    #if nasBackup:
        #server = '147.47.228.192'
        #for subjectClass in subjectClassList:
            #copiedDir = os.path.dirname(subjectClass.targetDir)
            #server_connect(server, copiedDir)
