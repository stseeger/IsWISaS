import os
import gzip
import datetime
import time
import sys
import collections

import support
import configLoader
import DataBuffer

class LogFileEntry():
    def __init__(self, time, data):
        self.time = time
        self.data = data

    def __repr__(self):
        return support.secs2String(self.time,"%Y-%m-%d %H:%M:%S") + str(self.data)


class ExtendedFileHandle():
    def __init__(self, handle, path, columnOfParameter, columnsOfTimeAndData):
        self.handle = handle
        self.path = path
        self.columnOfParameter = columnOfParameter
        self.columnsOfTimeAndData = columnsOfTimeAndData

class Reader():
    def __init__(self, configFile, logDir, logScheme = '?', bufferSize = 4000, startTimeFromFilepathFun = None, fillBuffer=True):
        self.logDir = logDir
        conf = configLoader.load_confDict(configFile)

        print(logDir)
        
        if logScheme == '?':
            logScheme = self.detect_logScheme(conf)
            print("Detected logFile scheme:", logScheme)
        self.logScheme = logScheme
        self.conf    = conf[logScheme]
        self.columns = collections.OrderedDict()
        self.units = collections.OrderedDict()
        for qualifier in ["essential","optional"]:
            if not qualifier+"Columns" in conf.keys():
                continue
            for key in conf[qualifier+"Columns"][logScheme].keys():
                self.columns[key] = conf[qualifier+"Columns"][logScheme][key]
                self.units[key] = conf[qualifier+"Columns"]["units"][key]

        self.current = None
        self.dataBuffer = None
        self.lastTime = 0
        self.bufferSize = bufferSize

        self.startTimeFromFilepathFun = startTimeFromFilepathFun

        if(fillBuffer):
            sys.stdout.write("Filling data buffer...")
            self.fill_dataBuffer()
            sys.stdout.write("done!\n")

    def list_logFiles(self, pattern = None, logDir = None):
        """
        Return a list of all files in a log directory matching a  naming pattern.

        Keyword arguments:
        pattern -- naming pattern of the logFiles (defaults to self.conf["logFilePattern"])
        logDir -- root directory of the logFiles (defaults to self.logDir)
        """
        
        if logDir is None:
            logDir = self.logDir
        if pattern is None:
            pattern = self.conf["logFilePattern"]
            
        pattern = "\/".join(support.formatStrings2RegEx(pattern).split('/'))
        matchingFiles = None
        try:
            # fail safe
            matchingFiles = support.recursiveFileList(logDir, pattern)
        except:
            matchingFiles = []
        return sorted(matchingFiles)

    def get_mostRecentLogFile(self):
        return self.list_logFiles()[-1]

    def raw_open_logFile(self, logFile, skipLines = 0, encoding="utf-8"):
        """
        Open a (possibly gzipped) logFile and return the file handler.

        Keyword arguments:
        logFile -- filepath of the logFile to open
        skipLines -- number of lines to skip (defaults to 0)
        enoding -- encoding of the log file (defaults to utf-8)
        """        
        filepath = self.logDir+'/'+logFile
        if logFile.endswith("gz"):            
            f = gzip.open(filepath,'rt',encoding=encoding)
        else:           
            f = open(filepath,'r', encoding=encoding)
        for i in range(int(skipLines)):
            l=f.readline()            
        return f

    def get_logFileHeader(self, logFile, logFileSpecs = None):
        """
        Return a tuple containing the header of a log file and the number of lines until the header occurs.

        Keyword arguments:
        logFile -- filepath of the logFile to open
        logFileSpecs -- dictionary with the keys 'skipLines', 'commentChar' and 'seperator' (defaults to self.conf)
        """
        if logFileSpecs is None:
            logFileSpecs = self.conf
        f = self.raw_open_logFile(logFile,
                                  skipLines = logFileSpecs["skipLines"],
                                  encoding = logFileSpecs["encoding"])                                
        n = logFileSpecs["skipLines"]
        # read single lines until a line does not start with a comment char
        # and consider this line to be the header
        header=None
        while header is None:
            line = str(f.readline())
            n+=1
            if not line.startswith(logFileSpecs["commentChar"]):
                header=support.split(line,logFileSpecs["seperator"])
        f.close()        
        return header, n

    def scan_logFileHeader(self, header, columnDict=None):
        """
        Looks for the indices of the entries of a dict within a list of strings.

        Keyword arguments:
        header -- a list of strings containing column names
        columnDict -- a dictionary where the keys are internal and the entries
                      log file column names (defaults to self.columns)
        
        Return arguments:
        (result, found) -- result: equivalent to columnDict, but entries are
                           indices where the entries of columnDict where found
                           within the header; found: number 
        """
        if columnDict is None:
            columnDict = self.columns
        
        result = collections.OrderedDict()
        found = []

        for key in columnDict.keys():
            index=None
            for i,entry in enumerate(header):
                if columnDict[key] in entry and len(columnDict[key]) == len(entry):            
                    index=i                    
                    break
            result[key] = index
            found.append(not index is None)
                    
        return result, found
        
    def detect_logScheme(self, conf):
        """
        Returns the name of the detected scheme of logfiles found in self.logDir.
        """
        fileLists = collections.OrderedDict()
        fileCounts = collections.OrderedDict()        
        
        # get lists of possible log files based on the specified naming patterns        
        #print('XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX')
        
        for key in conf.keys():            
            if key in ["essentialColumns", "optionalColumns", "confFile"]:
                continue            

            fileLists[key] = self.list_logFiles(conf[key]["logFilePattern"])
            fileCounts[key] = len(fileLists[key])            

        # select all naming patterns that return any possible log file
        candidates = collections.OrderedDict()
        for key in fileCounts.keys():
            if fileCounts[key]:
                candidates[key] = collections.OrderedDict()

        # scan the first logFile for each log file scheme
        maxScore = 0
        for candidate in candidates.keys():            

            header, n = self.get_logFileHeader(fileLists[candidate][0], conf[candidate])            

            # now scan the header for columns specified in the configuration file
            for qualifier in ["essential","optional"]:                    
                candidates[candidate][qualifier+"Columns"], candidates[candidate][qualifier+"Matches"] =\
                                    self.scan_logFileHeader(header, conf[qualifier+"Columns"][candidate])                

            # in case all essential and optional columns were found, directly return the current candidate
            #if min(candidates[candidate]["essentialMatches"] + candidates[candidate]["optionalMatches"]):
             #   return candidate

            # compute a score for the candidate which is always zero if one essential column is missing
            candidates[candidate]["score"] = min(candidates[candidate]["essentialMatches"]) * (1+sum(candidates[candidate]["optionalMatches"]))

            #keep track of the achieved maximum score
            maxScore = max([maxScore, candidates[candidate]["score"]])


        # in case no candidate yielded a perfect result, take the best one (all essential columns and most optional ones)
        for candidate in candidates.keys():
            if candidates[candidate]["score"]>0 and candidates[candidate]["score"] == maxScore:
                return candidate

        logDir = self.logDir
        raise Exception(logDir + " does not seem to contain usable logFiles...")

    def open_logFile(self, logFile, fallbackFile = None):
        """
        Scans the header of a log file and returns a file handler.
        """

        # this loop is needed to prevent problems that may occur when
        #   a new log file already exists, but does not yet contain any data
        for filepath in [logFile, fallbackFile]:
            header, n = self.get_logFileHeader(filepath)        
            pos, available = self.scan_logFileHeader(header)
            if True in available:
                break

        logFile = filepath
        
        colIndices={"time":[], "data":[]}        
        for column in pos.keys():
            if column in self.conf["timeColumns"]:
                colIndices["time"].append(pos[column])
            else:
                if not pos[column] is None:
                    colIndices["data"].append(pos[column])

        f = self.raw_open_logFile(logFile, n)

        self.current = ExtendedFileHandle(handle = f,
                                          path = logFile,
                                          columnOfParameter = pos,
                                          columnsOfTimeAndData= colIndices)        

        return f

    def parse_logFileLine(self, rawLine):
        """
        Parses a raw logfile line into a LogFileEntry object (containing timestamp and data entries).
        """
        colIndices = self.current.columnsOfTimeAndData
        line = support.split(rawLine, self.conf["seperator"])        
        # get components of time info, combine them and convert to unix timestamp
        t = [line[x] for x in colIndices["time"]]
        t = ' '.join(t)        
        #t = datetime.datetime.strptime(t, self.conf["timeFormatString"])
        #t = time.mktime(t.timetuple())
        t = support.string2Secs(t, self.conf["timeFormatString"])

        #print(line)
        
        # best case: all entries are numeric
        try:
            data = [float(line[x]) for x in colIndices["data"]]
        # fallback: at least one entry cannot be converted to float
        except:
            data = []
            for i in colIndices["data"]:
                if i is None:
                    entry = 0
                else:
                    try:
                        entry = float(line[i])
                    except:                    
                        entry = line[i]
                data.append(entry)
            

        return LogFileEntry(t, data)

    def scan_logFileTime(self, filepath, onlyFirst = True):
        """
        Returns the first (and optionaly last) time within a log file
        """

        if onlyFirst and not self.startTimeFromFilepathFun is None:
            return self.startTimeFromFilepathFun(filepath)
        
        f=self.open_logFile(filepath)
        posA = f.tell()

        try:
            firstTime = self.parse_logFileLine(f.readline()).time
        except:
            firstTime = None

        if onlyFirst:
            return firstTime        
            
        posB = f.tell()
        f.seek(0,2) # go to end of file
        posC = f.tell()

        lineSize = posB-posA
        lineCount = (posC-posA)/lineSize        

        lastTime = None
        for n in range(1,5):            
            try:                
                f.seek((lineCount-n)*lineSize,0) # jump n lines before the end of the file
                x = f.readline()                
                lastTime = self.parse_logFileLine(x).time
                break
            except:
                pass

        return firstTime, lastTime

    def filter_logFiles(self, newerThan, olderThan=None):
        """
        Returns all log files that are newer (and optionally older) than a specified time
        """
        fileList = self.list_logFiles()

        if isinstance(newerThan, str):
            newerThan = support.string2Secs(newerThan)

        if not olderThan is None:
            if isinstance(olderThan, str):
                olderThan = support.string2Secs(olderThan)

        filteredFileList = []
        for file in fileList:
            t = self.scan_logFileTime(file, onlyFirst=True)            
            if (newerThan is None) or  (t >= newerThan):
                if (olderThan is None) or (t <= olderThan):                
                    filteredFileList.append(file)

        return filteredFileList
            
    def read_logFile(self, filepath, dataBuffer):
        """
        Reads a complete (all lines are expected to be complete) log file into a dataBuffer
        """        
        f = self.open_logFile(filepath)
        for rawLine in f.readlines():           
            entry = self.parse_logFileLine(rawLine)
            dataBuffer.add(entry.data, entry.time)
        return dataBuffer

    def update(self, dataBuffer=None, proceed=True):
        """
        Read data from the currently opened log file to a dataBuffer

        Keyword arguments:
        dataBuffer -- dataBuffer object to read to (if None, then self.dataBuffer is used)
        proceed -- boolean value to indicate, whether a more recent logfile should be opened
        """

        f = self.current.handle
        if dataBuffer is None:
            dataBuffer = self.dataBuffer
        
        fine = True
        while fine:
            lastPos = f.tell()
            rawLine = f.readline()
            #print(rawLine)
            try:
                entry = self.parse_logFileLine(rawLine)
                dataBuffer.add(entry.data, entry.time)               
            except:
                fine = False
                f.seek(lastPos)

        if proceed:
            latestLogFile = self.get_mostRecentLogFile()            
            if  not self.current.path == latestLogFile:                
                self.open_logFile(latestLogFile, self.current.path)
                self.update(dataBuffer)

        return dataBuffer


    def create_dataBuffer(self, bufferSize = 4000):
        """
        Creates a data dataBuffer object that can hold the data of the log file
        """
        reverseColumnDict = support.reverse_dict(self.columns)
        parList = []
        for column in self.columns.keys():            
            if self.columns[column] in self.conf["timeColumns"] or self.columns[column] == '?':
                continue            
            parList.append(DataBuffer.Parameter(name = column, unit=self.units[column]))

        return DataBuffer.Buffer(bufferSize, None, parList)
    

    def fill_dataBuffer(self, dataBuffer=None, startTime=None, endTime=None):
        """
        Returns a dataBuffer filled with log file data
        """
        if dataBuffer is None:
            dataBuffer = self.create_dataBuffer(self.bufferSize)
            self.dataBuffer = dataBuffer

        if startTime is None:
            startTime = self.scan_logFileTime(self.get_mostRecentLogFile())
        elif type(startTime) is str:
            startTime = support.string2Secs(startTime)
        else:
            firstTime, lastTime = self.scan_logFileTime(self.get_mostRecentLogFile(), onlyFirst=False)            
            startTime = lastTime + startTime       

        logFileList = self.filter_logFiles(startTime, endTime)        

        for filepath in logFileList[:-1]:            
            self.read_logFile(filepath, dataBuffer)

        if len(logFileList)>1:
            self.open_logFile(logFileList[-1], logFileList[-2])
        else:            
            self.open_logFile(logFileList[-1])
            
        self.update(dataBuffer, proceed=False)

        return dataBuffer

            
if __name__ == "__main__":

    #configFile = "../config/logDescriptors/IsWISaS_valveLog.lgd"
    #t = Reader(configFile, "../log")

    #print(t.dataBuffer.get_time())

    configFile = "../config/logDescriptors/picarroLxxxx-i.lgd"
    logDir = "C:/UserData/DataLog_User"
    #logDir = "../exampleLogs/2120"
    #logDir = "../../../picarroLogs/fake"
    
    s = Reader(configFile, logDir, "?")    
            
