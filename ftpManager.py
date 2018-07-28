#!/usr/bin/env python3

import json
import re
import os
import subprocess

from pprint import pprint
from ftplib import FTP
from os import path as ospath
from datetime import datetime

from nvrVideoEditor import concatenateVideos            #Imports the script which concatenates all the mp4 files in the directory


class fileData:
    fileWithPath = ""

    def __init__(self, fileWithPath):
        self.fileWithPath = fileWithPath

        if fileWithPath.endswith("mp4"):
            self.fileType = "mp4"
        elif fileWithPath.endswith("jpg"):
            self.fileType = "jpg"
        else:
            raise Exception("FileTypeNotSupported")

    def getFileTime(self):
        if self.fileType == "mp4":
            print("")
        elif self.fileType == "jpg":
            print("")
        else:
            raise Exception("FileTypeNotSupported")

    def getFileDate(self):
        return re.search(r"/(20[0-9][0-9]-[0-9][0-9]-[0-9][0-9])/", self.fileWithPath).group(1)

    def getFileYear(self):
        return int(re.search(r"20[0-9][0-9]", self.getFileDate()).group())

    def getFileMonth(self):
        return int(re.search(r"-([0-9][0-9])-", self.getFileDate()).group(1))

    def getFileDay(self):
        return int(re.search(r"-([0-9][0-9])$", self.getFileDate()).group(1))

    def getCameraName(self):
        return re.search(r"FTP/([\w]+)/", self.fileWithPath).group(1)


class FTPWalk:
    """
    This class is contain corresponding functions for traversing the FTP
    servers using BFS algorithm.
    https://stackoverflow.com/questions/31465199/extending-pythons-os-walk-function-on-ftp-server
    """
    def __init__(self, connection):
        self.connection = connection

    def listdir(self, _path):
        """
        return files and directory names within a path (directory)
        """

        file_list, dirs, nondirs = [], [], []
        try:
            self.connection.cwd(_path)
        except Exception as exp:
            print("the current path is : ", self.connection.pwd(), exp.__str__(),_path)
            return [], []
        else:
            self.connection.retrlines('LIST', lambda x: file_list.append(x.split()))
            for info in file_list:
                ls_type, name = info[0], info[-1]
                if ls_type.startswith('d'):
                    dirs.append(name)
                else:
                    nondirs.append(name)
            return dirs, nondirs

    def walk(self, path='/'):
        """
        Walk through FTP server's directory tree, based on a BFS algorithm.
        """
        dirs, nondirs = self.listdir(path)
        yield path, dirs, nondirs
        for name in dirs:
            path = ospath.join(path, name)
            yield from self.walk(path)
            self.connection.cwd('..')
            path = ospath.dirname(path)


with open('ftp_details.json', 'r') as serverDetails:
    serverData = json.load(serverDetails)

#pprint(serverData)				#Prints FTP JSON data

ftp = FTP(serverData["ftp"]["hostname"])        # connect to host, default port
ftp.login(user=serverData["ftp"]["username"],passwd=serverData["ftp"]["password"])	    # user, passwd from JSON file
ftp.cwd(serverData["ftp"]["path"])              # change into "debian" directory
ftp.retrlines('LIST')                           # list directory contents
ftp.dir()

ftpwalk = FTPWalk(ftp)

prevMP4Year = 0
prevMP4Month = 0
prevMP4Day = 0
prevCameraName = ""

for i in ftpwalk.walk():
    #print(i)
    #print("FTP Path: "+i[0])
    #print("Directories - list")
    #print(i[1])
    #print("Files - list")
    #print(i[2])

    try:
        ftp.rmd(i[0])
        print("Deleted Directory: "+i[0])
    except:
          pass

    for fileName in i[2]:
        if fileName.endswith("mp4"):

            fileDetails = fileData(i[0] + "/" + fileName)
            print("Camera Name: "+fileDetails.getCameraName()+" | File Year: "+str(fileDetails.getFileYear())+
                  " | File Month: "+str(fileDetails.getFileMonth())+" | File Day: "+str(fileDetails.getFileDay()))

            if prevMP4Year == 0:
                prevMP4Year = fileDetails.getFileYear()
                prevMP4Month = fileDetails.getFileMonth()
                prevMP4Day = fileDetails.getFileDay()
                prevCameraName = fileDetails.getCameraName()

            if datetime(fileDetails.getFileYear(), fileDetails.getFileMonth(), fileDetails.getFileDay()) > \
                    datetime(prevMP4Year, prevMP4Month, prevMP4Day):

                print("Merge Previously Downloaded Files")
                concatenateVideos(os.getcwd()+"/videos",
                                  prevCameraName+"-"+str(prevMP4Year)+"-"+str(prevMP4Month)+"-"+str(prevMP4Day))

                print("Upload the merged file")
                uploadOutput = subprocess.run(["python3", "youtubeUpload.py", "--file",
                        os.getcwd()+"/videos/"+prevCameraName+"-"+str(prevMP4Year)+"-"+str(prevMP4Month)+"-"+str(prevMP4Day),
                        "--title", prevCameraName+"-"+str(prevMP4Year)+"-"+str(prevMP4Month)+"-"+str(prevMP4Day),
                        "--description", prevCameraName+"-"+str(prevMP4Year)+"-"+str(prevMP4Month)+"-"+str(prevMP4Day),
                        "--keywords", "CCTV"],capture_output=True)

                if re.search(r"was successfully uploaded", uploadOutput.stdout.decode('utf-8')):
                    print("File "+prevCameraName+"-"+str(prevMP4Year)+"-"+str(prevMP4Month)+"-"+str(prevMP4Day)
                          + "was successfully uploaded to YouTube")
                else:
                    print(uploadOutput)

                    if re.search(r"exceeded", uploadOutput.stdout.decode('utf-8')) or \
                            re.search(r"exceeded", uploadOutput.stderr.decode('utf-8')):
                        print("Something Exeeded, Exitting Application")
                        exit(1)

                print("Delete the downloaded, merged files")
                deleteFiles = subprocess.run(["rm", os.getcwd()+"/videos/"+'*.mp4'], capture_output=True)
                prevMP4Year = fileDetails.getFileYear()
                prevMP4Month = fileDetails.getFileMonth()
                prevMP4Day = fileDetails.getFileDay()
                prevCameraName = fileDetails.getCameraName()

            if datetime(fileDetails.getFileYear(), fileDetails.getFileMonth(), fileDetails.getFileDay()) < \
                    datetime(datetime.now().year, datetime.now().month, datetime.now().day):
                print("Downloading the file "+fileDetails.fileWithPath)
                ftp.retrbinary('RETR ' + fileDetails.fileWithPath, open(os.getcwd()+"/videos/"+fileName, 'wb').write)
                #ftp.delete(i[0] + "/" + fileName)


        elif fileName.endswith("jpg"):
            print("Upload "+i[0]+"/"+fileName+" to Flickr")
        else:
            print("Delete the file "+i[0]+"/"+fileName)
            ftp.delete(i[0]+"/"+fileName)

    print("===================")

ftp.quit()

