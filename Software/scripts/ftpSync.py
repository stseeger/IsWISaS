import ftplib
import time
import GUI_Picarro
import os
import subprocess
import tkinter as tk
import datetime
import shutil

#ftpBaseDir = "incoming/loggerqWeRtZuIoP1742/Remote_Picarros/Rietholzbach"
ftpBaseDir = "htdocs/Ettenheim"
firstTimeString = "2021-06-08"
class ftpHandler:
    def __init__(self, baseDir):
        self.baseDir = baseDir
        print("connect to ftp...")
        #self.ftp = ftplib.FTP('132.230.1.7','anonymous')
        self.ftp = ftplib.FTP('ftpupload.net')
        self.ftp.login(user='unaux_28839732',passwd='ecohydro')
       

    def __del__(self):
        try:
            self.ftp.quit()
            print("ftp connection closed politely")
        except:
            self.ftp.close()
            print("ftp connection closed unilaterally")

    def listdir(self, dirname):
            
        lines = []
        dirlist = self.ftp.dir(self.baseDir + '/' + dirname, lines.append)

        thisYear = datetime.datetime.now().year

        info = []
        for line in lines:
            tokens = line.split(maxsplit = 9)
            name = tokens[8]
            time_str = tokens[5] + " " + tokens[6] + " " + tokens[7]
            try:
                dt = datetime.datetime.strptime("%d "%thisYear +time_str, "%Y %b %d %H:%M")
            except:
                dt = datetime.datetime.strptime(time_str, "%b %d %Y")
            
            posix = time.mktime(dt.timetuple())
            info.append([name,posix])

        return info

    def delete(self, filepath):
        print("delete from ftp: " + filepath)    
        self.ftp.delete('%s/%s'%(self.baseDir, filepath))

    def pull(self, filepath, destFilePath):
        print("retrieve from ftp: " + filepath + ' -> ' + destFilePath)
        with open(destFilePath, "wb") as confFile:
            self.ftp.retrbinary('RETR %s/%s'%(self.baseDir, filepath), confFile.write)       

    def push(self, filename, destFilename=None, append=False):    
        if destFilename is None:
            destFilename = filename.split('/')[-1]         

        print("uploading " + filename + ' -> ' + destFilename)
        with open(filename,'rb') as fileObj:           
            self.ftp.storbinary('%s %s/%s'%(["STOR","APPE"][append],self.baseDir, destFilename), fileObj)

    def push_update(self, filename, destFilename=None, sep='\t'):

        fileLines = open(filename).readlines()

        base_filename = filename.split('/')[-1].split('.')[0]
        lastline_filename =  '../temp/' + base_filename + '.last'
        newlines_filename = '../temp/' + base_filename + '.new'

        if os.path.isfile(lastline_filename):
            lastLine = open(lastline_filename).readlines()[-1]            
            last_pushed_time = lastLine.split(sep)[0]

            new_lines = []
            for i in range(len(fileLines)-1,0,-1):
                lineTime = fileLines[i].split(sep)[0]
                if lineTime > last_pushed_time:
                    new_lines.insert(0, fileLines[i])
                else:
                    break
            append = True
        else:
            new_lines = fileLines
            append = False

        if len(new_lines):
            
            n = max(10, len(new_lines))
            new_lines = new_lines[:n]

            print("\tuploading %d new lines..."%len(new_lines))

            with open(newlines_filename,"w") as update:
                update.writelines(new_lines)

            if destFilename is None:
                destFilename = filename.split('/')[-1]

            self.push(newlines_filename, destFilename, append)

            with open(lastline_filename, 'w') as refFile:
                refFile.write(fileLines[-1])

        else:
            print("\tno new lines since last upload.")

def sync_server_to_local():

    ftp = ftpHandler(ftpBaseDir)
    remoteConfigFiles = ftp.listdir('remote_config')

    restart = False
    reboot = False

    for remoteConfigFile in remoteConfigFiles:
        filename = remoteConfigFile[0]                
        modTime = remoteConfigFile[1]

        if filename == "reboot.now":
            reboot = True
            ftp.delete("remote_config/reboot.now")
            continue
            
        
        localFilePath = "config/%s"%filename        
        if os.path.isfile(localFilePath):            
            if os.path.getmtime(localFilePath) >= modTime:
                continue

        restart = True        
        # retrieve file from ftp-server
        ftp.pull("remote_config/%s"%filename,localFilePath)
        # set last modification time of local file to that of file on the server
        os.utime(localFilePath, (modTime, modTime))
   
    return restart, reboot
    


if __name__ == "__main__":

    if 0:

        #-----------
        print(30*"#"+"\nsynchronize: server -> local disk")
        restart, reboot = sync_server_to_local()            
        if restart:
            open("temp/restart.now","w").write(GUI_Picarro.secs2DateString(time.time(),"%Y-%m-%d %H:%M:%S"))
        if reboot:
            open("temp/reboot.now","w").write(GUI_Picarro.secs2DateString(time.time(),"%Y-%m-%d %H:%M:%S"))        

    #-----------
    print(30*"#"+"\nsynchronize: local disk -> server")        
    

    print("update \"valves.log\"...")
    valveDat = open("../log/valves.log").readlines()
    #valveDat = list(map(lambda x: '\t'.join(x.split(";")[1:]), valveDat))
    open("../temp/valves.log",'w').writelines(valveDat)
    
    
    print("update \"recentH2O.txt\"...")
    subprocess.Popen("python PicarroPeeker.py").communicate()
    recentH2OFile = open("../temp/recentH2O.log").readlines(1)[0]\
                    .replace("#","").replace("\n","")

    print("------")


    ftp = None
    for i in range(10):
        try:
            ftp = ftpHandler(ftpBaseDir)
            break
        except:
            print("\tcould not connect to ftp, retrying...")

    for i in range(10):        
        try:
            ftp.push_update("../temp/valves.log", "/logfiles/valves.log")
            break
        except:
            print("\tcould not upload valve data, retrying...")

    for i in range(10):
        try:
            ftp.push_update("../temp/recentH2O.log", "/logfiles/picarroDaily/"+recentH2OFile)
            break
        except:
            print("\tcould not upload picarro data, retrying...")
        

    del ftp
    print("------")
