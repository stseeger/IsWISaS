import LogFileReader
import os
import datetime
import time
#import rdp

timeWindow_in_hours = 1

configFile = "../config/logDescriptors/picarroLxxxx-i.lgd"
logDir = "C:/UserData/DataLog_User" 
lfr = LogFileReader.Reader(configFile, logDir, "?", fillBuffer=False)
        
#logFiles = GUI_Picarro.listLogFiles(logDir)
logFiles = lfr.list_logFiles(lfr.conf['logFilePattern'],logDir)


timeFormatString = "%Y-%m-%d %H:%M:%S"
#timeFormatString = "%Y-%m-%d %H:%M:%S"

columns = ["DATE","TIME","H2O","Delta_18_16", "Delta_D_H"]
indexDict = {}

full_times = []
full_values = []
full_valPairs = []

now = time.time()

fileIndex = len(logFiles)-1
firstTime = None
lastTime = None
timeSpan = 0

while timeSpan < timeWindow_in_hours*3600:
    print("process \"%s\""%logFiles[fileIndex])
    with open(logDir+'/'+logFiles[fileIndex]) as f:

        times = []
        values = []
        valPairs = []
        
        firstLine = f.readline()
        for col in columns:
            indexDict[col] = firstLine.find(col+' ')

        for line in f.readlines():

            try:
            
                i = indexDict["DATE"]
                timeString =  line[i:i+20].strip()
                i = indexDict["TIME"]
                timeString += ' ' +  line[i:i+20].strip().split('.')[0]
                dt = datetime.datetime.strptime(timeString, timeFormatString)
                posixTime = time.mktime(dt.timetuple())

                if  len(valPairs) and (posixTime - valPairs[-1][0]) < 5:
                    continue
                
                i = indexDict["H2O"]
                valueH2O = int(float(line[i:i+20].strip()))
                i = indexDict["Delta_18_16"]
                value18O = round(float(line[i:i+20].strip()),2)
                i = indexDict["Delta_D_H"]
                value2H = round(float(line[i:i+20].strip()),2)

                valPairs.append([posixTime, valueH2O, value18O,value2H])
            except:
                pass

    timeSpan = valPairs[-1][0] - valPairs[0][0]
    fileIndex-=1

# use Ramer-Douglas-Peucker algorithm to simplify the time series
#print("original # of data points:",len(full_valPairs))
#print("reduce number of data points...")
simple = valPairs#rdp.rdp(full_valPairs, epsilon=50)
#print("reduced # of data points:",len(simple))

baseTime = 0#full_valPairs[0][0]

fileTimeStamp = "%s.log"%(logFiles[-1].split('/')[-1].split('-')[1])

with open("../temp/recentH2O.log", "w") as f:
    f.write("#"+fileTimeStamp+'\n')
    f.write("time\tH2O\tdelta18O\tdeltaD\n")
    f.write("\n".join(map(lambda x: "%.0f\t%d\t%.2f\t%.2f"%(x[0]-baseTime,x[1],x[2],x[3]), simple)))
    f.write("\n")
