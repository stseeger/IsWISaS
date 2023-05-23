import LogFileReader
import os
import datetime
import time
import support

#def peek(backwardsHours = 24, logDir = "D:/Seeger/picarroLogs/2140"):
def peek(backwardsHours = 24, logDir = "C:/UserData/DataLog_User", timeWindow=None):

    configFile = "../config/logDescriptors/picarroLxxxx-i.lgd"
    lfr = LogFileReader.Reader(configFile, logDir, "?", fillBuffer=False)
    logFiles = lfr.list_logFiles(lfr.conf['logFilePattern'],logDir)

    #print("~~~~~~~~~")
    #print(logDir)
    #print(logFiles)    

    timeFormatString = "%Y-%m-%d %H:%M:%S"
    columns = ["DATE","TIME","H2O", "Delta_18_16", "Delta_D_H",  "Delta_17_16"]
    indexDict = {}

    full_times = []
    full_values = []
    full_valPairs = []

    now = time.time()

    fileIndex = len(logFiles)-1
    firstTime = None
    lastTime = None
    timeSpan = 0

    #while timeSpan < backwardsHours*3600:  

    while (fileIndex>=0) and (timeWindow is None or firstTime is None or firstTime > timeWindow[0]):

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

                    #if posixTime > timeWindow[1]:
                     #   break
                    
                    i = indexDict["H2O"]
                    valueH2O = int(float(line[i:i+20].strip()))

                    i = indexDict["Delta_18_16"]
                    value18O = round(float(line[i:i+20].strip()),2)  

                    i = indexDict["Delta_D_H"]
                    value2H = round(float(line[i:i+20].strip()),2)                                      

                    i = indexDict["Delta_17_16"]
                    if i > 0:
                        value17O = round(float(line[i:i+20].strip()),2)
                        valPairs.append([posixTime, valueH2O, value18O, value2H, value17O])
                    else:
                        valPairs.append([posixTime, valueH2O, value18O, value2H])

                    
                except:
                    pass

        full_valPairs = valPairs + full_valPairs        
        timeSpan = full_valPairs[-1][0] - full_valPairs[0][0]


        if timeWindow is None:
            timeWindow = [full_valPairs[-1][0] - backwardsHours*3600, full_valPairs[-1][0]]

        firstTime = full_valPairs[0][0]        
        fileIndex-=1

        print(fileIndex, support.secs2String(firstTime), support.secs2String(timeWindow[0]))
        print(len(full_valPairs))

    return full_valPairs

if __name__ == "__main__":

    peekDat = peek()
    if len(peekDat[0]) == 5:
        with open("../temp/recentH2O.log", "w") as f:
            f.write("#%d"%time.time()+'\n')
            f.write("time\tH2O\tdelta18O\tdeltaD\tdelta17O\n")
            f.write("\n".join(map(lambda x: "%.0f\t%d\t%.2f\t%.2f\t%.2f"%(x[0],x[1],x[2],x[3],x[4]), peekDat)))
            f.write("\n")
    else:
        with open("../temp/recentH2O.log", "w") as f:
            f.write("#%d"%time.time()+'\n')
            f.write("time\tH2O\tdelta18O\tdeltaD\n")
            f.write("\n".join(map(lambda x: "%.0f\t%d\t%.2f\t%.2f"%(x[0],x[1],x[2],x[3]), peekDat)))
            f.write("\n")
