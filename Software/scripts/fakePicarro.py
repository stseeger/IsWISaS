import os
import shutil
import time
import math

from support import secs2String

model = "2130"

if model == "2130":
    origDir = "../../../picarroLogs/2130"
else:
    origDir = "../../../picarroLogs/RHB3"


fakeDir = "../../../picarroLogs/fake"

print("==== Starting FakePicarro ========")
print("source directory: "+origDir)
print("target directory: "+fakeDir)
print("----------------------------------")
print("clean up target directory")
for entry in os.listdir(fakeDir):
    shutil.rmtree(fakeDir+'/'+entry)

#-----------------------------------
#-----------------------------------

dirList = os.listdir(origDir)

if len(dirList[0]) == 4:
    newDirList = []
    for year in dirList:
        monthDirList = os.listdir(origDir+'/'+year)
        for month in monthDirList:
            for day in os.listdir(origDir+'/'+year + '/' + month):
                newDirList.append(year + '/' + month + '/' +day)
    dirList = newDirList

print(dirList)


#if model != "2130":

# skip first 60 days in source directory
skip=0

for entry in dirList:
    if skip:
        skip -= 1
        continue

    subDirList = list(filter(lambda x: x.endswith(".dat"),
                                  os.listdir(origDir+'/'+entry)))
    os.makedirs(fakeDir+'/'+entry, exist_ok=True)

    for subEntry in subDirList:
        print(subEntry)
        lines = open(origDir+'/'+entry+'/'+subEntry).readlines()        
        
        
        with open(fakeDir+'/'+entry+'/'+subEntry,'a') as outFile:            
            outFile.write(lines[0])
            for line in lines[1:]:
                now = time.time()
                datePart = secs2String(now, "%Y-%m-%d                ")
                timePart = secs2String(now, "%H:%M:%S")
                fracSecPart = ("%.3f              "%(now - math.floor(now)))[1:]                              
                modLine = datePart + timePart + fracSecPart + line[52:]

                if len(line)!= len(modLine):
                    stumble()
                
                outFile.write(modLine)
                outFile.flush()                
                time.sleep(1)
                
        
