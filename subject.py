# -*- coding: utf-8 -*-
'''
# Back up data and forms a database from the MRI data
# Created by Kang Ik Kevin Cho
# Contributors: Dahye Stella Bae, Eunseo Cho
'''
from __future__ import division
import os
import dicom
import re
import pandas as pd
import getpass

from progressbar import AnimatedMarker,ProgressBar,Percentage,Bar
class subject(object):
    def __init__(self, subjectDir, dbLoc):
        self.location = subjectDir

        dicomDirDict = {}

        pbar = ProgressBar()
        for root, dirs, files in os.walk(self.location):
            dicoms = []
            for oneFile, i in zip(files, pbar(range(6000))):
                if re.search('(dcm|ima)', oneFile, re.IGNORECASE):
                    dicoms.append(os.path.join(root,oneFile))
            if not dicoms == [] : dicomDirDict[root] = dicoms

        self.dicomDirs = dicomDirDict
        self.dirs = dicomDirDict.keys()
        #self.allDicoms = reduce(lambda x, y: x + y, dicomDirDict.values())
        #self.allDicomNum = len(self.allDicoms)
        self.dirDicomNum = [(x,len(y)) for (x,y) in dicomDirDict.items()]
        self.firstDicom = next(iter(self.dicomDirs.values()))[0]
        self.modalityMapping = [modalityMapping(x) for x in self.dirs]
        self.modalityDicomNum = dict(zip(self.modalityMapping, [x[1] for x in self.dirDicomNum]))

        ds = dicom.read_file(self.firstDicom)
        self.age = re.search('^0(\d{2})Y',ds.PatientAge).group(1)
        self.dob = ds.PatientBirthDate
        self.id = ds.PatientID
        self.surname = ds.PatientName.split('^')[0]
        self.name = ds.PatientName.split('^')[1]
        try:
            self.fullname = ''.join([x[0].upper()+x[1:].lower() for x in [self.surname, self.name.split(' ')[0], self.name.split(' ')[1]]])
            self.initial = self.surname[0]+''.join([x[0] for x in self.name.split(' ')])
        except:
            self.fullname = ''.join([x[0].upper()+x[1:].lower() for x in [self.surname, self.name]])
            self.initial = self.surname[0]+self.name[0]
        
        self.sex = ds.PatientSex
        self.date = ds.StudyDate
        self.experimenter = getpass.getuser()

        print('Now collecting information for')
        print('==============================')
        print('\n\t'.join([self.location, self.fullname, self.initial, self.id, self.dob, 
                           self.date, self.sex, ', '.join(self.modalityMapping),
                           'by ' + self.experimenter]))
        print('==============================')

        self.koreanName = input('Korean name  ? eg. 김민수: ')
        self.note = input('Any note ? : ')
        self.group = input('Group ? : ')
        self.numberForGroup = maxGroupNum(os.path.join(dbLoc, self.group))
        self.study = input('Study name ? : ')
        self.timeline = input('baseline or follow up ? eg) baseline, 6mfu, 1yfu, 2yfu : ') #bienseo: Solve unicode-error problems
        
        #bienseo: Classify timeline(baseline or follow up)

        if self.timeline != 'baseline':
            df = pd.ExcelFile(os.path.join(dbLoc,'database','database.xls')).parse(0)
           
            self.folderName = df.ix[(df.timeline=='baseline') & (df.patientNumber == int(self.id)), 'folderName'].values.tolist()[0]
            #bienseo: Show back up folder name
            print('\n\n       Now Back up to       ' + self.folderName + '\n\n')
            self.targetDir = os.path.join(dbLoc,
                                          self.group,
                                          self.folderName,
                                          self.timeline)
        else:
            self.folderName = self.group + self.numberForGroup + '_' + self.initial
            self.targetDir = os.path.join(dbLoc,
                                          self.group,
                                          self.folderName,
                                          self.timeline)    


def modalityMapping(directory):
    t1 = re.compile(r'^t1_\d{4}',re.IGNORECASE)
    t2 = re.compile(r'^t2_\d{4}',re.IGNORECASE)
    scout = re.compile(r'scout',re.IGNORECASE)
    rest = re.compile(r'rest\S*lr_sbref_\d{4}',re.IGNORECASE)
    restRef = re.compile(r'rest\S*lr(_sbref){2}',re.IGNORECASE)
    restBlipRL = re.compile(r'rest\S*blip_rl',re.IGNORECASE)
    restBlipLR = re.compile(r'rest\S*blip_lr',re.IGNORECASE)
    dti3 = re.compile(r'dti\S*B30',re.IGNORECASE)
    dti2 = re.compile(r'dti\S*B20',re.IGNORECASE)
    dti1 = re.compile(r'dti\S*B10',re.IGNORECASE)
    dtiBlipRL = re.compile(r'dti\S*rl_\d{4}',re.IGNORECASE)
    dtiBlipLR = re.compile(r'dti\S*lr_\d{4}',re.IGNORECASE)


    for modality in (t1,'T1'),(t2,'T2'),(scout,'SCOUT'),(rest,'REST'),(restRef,'REST_REF'),(restBlipRL,'REST_BLIP_RL'),(restBlipLR,'REST_BLIP_LR'),(dti3,'DTI_3000'),(dti2,'DTI_2000'),(dti1,'DTI_1000'),(dtiBlipRL,'DTI_BLIP_RL'),(dtiBlipLR,'DTI_BLIP_LR'):
        basename = os.path.basename(directory)
        try:
            matchingSource = modality[0].search(basename).group(0)
            return modality[1]
        except:
            pass
    return directory


def maxGroupNum(backUpTo):
    maxNumPattern=re.compile('\d+')

    mx = 0
    for string in maxNumPattern.findall(' '.join(os.listdir(backUpTo))):
        if int(string) > mx:
            mx = int(string)

    highest = mx +1

    if highest<10:
        highest ='0'+str(highest)
    else:
        highest = str(highest)

    return highest

