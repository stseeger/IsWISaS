import os
import shutil
import time

origDir = "../../../picarroLogs/RHB3"
fakeDir = "../../../picarroLogs/fake"


print("==== Starting FakePicarro ========")
print("source directory: "+origDir)
print("target directory: "+fakeDir)
print("----------------------------------")

print("clean up target directory")
for entry in os.listdir(fakeDir):
    shutil.rmtree(fakeDir+'/'+entry)

dirList = os.listdir(origDir)

# skip first 60 days in source directory
skip=60

for entry in dirList:
    if skip:
        skip -= 1
        continue

    subDirList = list(filter(lambda x: x.endswith("Data.dat"),
                                  os.listdir(origDir+'/'+entry)))
    os.mkdir(fakeDir+'/'+entry)

    for subEntry in subDirList:
        print(subEntry)
        lines = open(origDir+'/'+entry+'/'+subEntry).readlines()
        
        with open(fakeDir+'/'+entry+'/'+subEntry,'a') as outFile:            
            outFile.write(lines[0])
            for line in lines[1:]:
                outFile.write(line)
                time.sleep(0.5)
                
        
