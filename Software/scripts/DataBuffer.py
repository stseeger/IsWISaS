import collections
import os
import itertools
import time
import copy
import support

class Parameter():
    def __init__(self, name, unit, relevantDifference=0):
        self.name = name
        self.unit = unit
        self.relevantDifference = relevantDifference       

    def __repr__(self):
        return "<DataBuffer.Parameter %s [%s]>"%(self.name,self.unit)

class Buffer():
    def __init__(self, length, filepath, parameters, flushChunk = 1, tag="buffer", saveEvery = 1):

        # save creation parameters
        self.length = length
        self.filepath = filepath
        self.saveEvery = saveEvery

        if not type(parameters) is list:
            parameters = [parameters]
        self.parameters = parameters

        self.flushChunk = [flushChunk, length] [flushChunk > length]
        self.tag=tag

        # create buffers
        self.recordBuffer = collections.deque([], length)
        self.timeBuffer = collections.deque([], length)
        self.dataBuffer = collections.deque([], length)        
        
        # some internal variables
        self.currentRecord = 0
        self.lastFlushRecord = 0        

    def copy(self):
        return copy.deepcopy(self)        

    def add(self, newData, newTime = None):
        
        # update record buffer
        self.currentRecord+=1

        # do not remember this step, if the record number is not
        # a multiple of the safeEvery argument passed on initialization
        # (it defaults to one, so that all added entries are actually saved)
        #print(self.currentRecord, self.currentRecord%self.saveEvery)
        if (self.currentRecord%self.saveEvery) > 0:
            return
        
        self.recordBuffer.append(self.currentRecord)

        # update time buffer
        if newTime is None: newTime = time.time()
        self.timeBuffer.append(newTime)
        
        # update data buffer
        if type(newData) is list:            
            self.dataBuffer.append(newData)
        else:
            self.dataBuffer.append([newData])     
                        
        # flush data to logfile in case the criteria are met
        if (self.currentRecord - self.lastFlushRecord) >= self.flushChunk:            
            self.flushToFile()        

    # get names of parameters in buffer
    def keys(self):
        return [p.name for p in self.parameters] 

    # get entries from the time buffer (all or starting at startIndex)
    def get_time(self, startIndex = None, timeOffset=0):
        if startIndex is None: startIndex = 0
        if startIndex < 0: startIndex = len(self.dataBuffer)+startIndex
        if not timeOffset:
            return list(itertools.islice(self.timeBuffer, startIndex, self.length))
        else:
            return [x+timeOffset for x in list(itertools.islice(self.timeBuffer, startIndex, self.length))]

    # get entries from the data buffer (all or starting at startIndex, or only for one specific parameter)
    def get_data(self, startIndex = None, parameter = None):

        if startIndex is None: startIndex = 0
        if startIndex < 0: startIndex = len(self.dataBuffer)+startIndex       

        if parameter is None:
            parameterMatch = [True for p in self.parameters]
        else:
            parameterMatch = list(map(lambda x: parameter==x, [y.name for y in self.parameters]))

        result = []
        for i, demand in enumerate(parameterMatch):
            if not demand:
                continue
            result.append(list(map(lambda x: x[i], itertools.islice(self.dataBuffer, startIndex, self.length))))

        return(result)

    def get_unit(self, parKey):
        for p in self.parameters:
            if p.name==parKey:
                return p.unit
       
    # wrapper to get_data implementing the [] operator
    def __getitem__(self, parKey):

        result = self.get_data(None, parKey)
        if len(result):
            return result[0]
        elif parKey=="time":
            return self.get_time()
        
        return None

    def writeHeader(self, filepath):
        
        f = open(filepath,'a')
                
        line1 ="#[%Y%m%d%H%M%S UTC]\t" + '\t'.join(["[%s]"%p.unit for p in self.parameters])
        line2 ="timestamp\t"     + '\t'.join([p.name for p in self.parameters])
        
        f.write(line1 + '\n' + line2 + '\n')
        f.close()

    def flushToFile(self):            
        if self.filepath is None: return

        filepath = support.insert_timeStamps(self.filepath) 
    
        # check if a log file already exists
        if not os.path.exists(filepath):
            # if needed, create directory for logfile
            fileDir = os.path.dirname(filepath)            
            if not os.path.exists(fileDir):
                print("create directory: " + fileDir)
                os.makedirs(fileDir)                
            # create logfile and write a header
            self.writeHeader(filepath)                    
        
        f = open(filepath,'a')

        #  ----- determine relevance of entries ------
        # start by deeming every time step relevant
        isRelevant = [True for x in self.timeBuffer]

        # in case any relevanceThreshold greater than 0 was defined, enter the follwoing loop
        relevanceThresholds = [p.relevantDifference for p in self.parameters]
        lastRelevant = self.dataBuffer[0]
        if max(relevanceThresholds) > 0:            
            for i, record  in enumerate(self.recordBuffer):

                # don't bother considering data that was already flushed
                if record <= self.lastFlushRecord:                    
                    continue

                # the very first record is always relevant
                if record==1:
                    continue
                
                # now check, whether at least one data value of the time step is different enough compared to its
                # pendant from the previous time step
                relevant = []
                #diff = []
                for last, current, threshold in zip(lastRelevant, self.dataBuffer[i], relevanceThresholds):                    
                    #diff.append(abs(last-current))
                    relevant.append(abs(last-current)>=threshold)                

                isRelevant[i] = max(relevant)
                if isRelevant[i]:                                        
                    # look, if there where some extreme values inbetween the last and the current relevant record
                    currentRelevant = self.dataBuffer[i]
                    intermediate = self.dataBuffer[i-1]

                    extremeInbetween = []
                    for last, intermediate, current in zip(lastRelevant, self.dataBuffer[i-1], self.dataBuffer[i]):
                        extremeInbetween.append(((last-intermediate) * (current-intermediate))>0)

                    isRelevant[i-1] = max(extremeInbetween)

                    # finally remember the current relevant record as the new last relevant
                    lastRelevant = self.dataBuffer[i]                    
                    
            
        #  ----- write relevant entries to the log file ------         
        for i, raw_time in enumerate(self.timeBuffer):

            if self.recordBuffer[i] <= self.lastFlushRecord or not isRelevant[i]:
                continue            
            
            format_time = time.strftime("%Y%m%d%H%M%S",time.gmtime(raw_time))
            line = format_time + '\t'           
            values = self.dataBuffer[i]
            line += '\t'.join(map(lambda x: str(x), values))
            f.write(line+'\n')

        self.lastFlushRecord = self.currentRecord
        f.close()

if __name__ == "__main__":

    import random

    parList = [Parameter(name = "valA", unit = "mL/min", relevantDifference = 40),
               Parameter(name = "valB", unit = "mL/min", relevantDifference = 60)]

    x = Buffer(20, "../temp/TEST_%Y%m%d%H.log", parList, flushChunk = 5)

    now = time.time()

    for i in range(20):        
        t = now+i*10
        v1 = round(random.random()*100)
        v2 = round(random.random()*200)
        x.add([v1,v2], t)

    #print(x.get_currentPath2())

    #print(x.
    
