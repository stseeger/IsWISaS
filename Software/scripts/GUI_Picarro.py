import tkinter as tk
from tkinter import font as tkFont
from collections import OrderedDict
import datetime
import time
import os
import sys
#-------------
import DataBuffer
import PlotCanvas
import configLoader
import ExtraWidgets
import MeasurementManager

#=====this might move down, but during development it is practical to find it here========================

#logDir = "C:/UserData"
logDir = "D:/Seeger/picarroLogs/1102"
firstTimeString = "2019-05-01"

#logDir = "D:\Seeger\Dropbox\PhD\Conventwald2\Data\picarroLogs"
if not os.path.exists(logDir):
    logDir = "C:/UserData/DataLog_User"    
    if not os.path.exists(logDir):
        logDir = "C:/UserData"
        

#=================== user setup ============================
# ---- some color definitions -----
COLOR_PLOTLINE = "#888"
COLOR_FAIL = "red"
COLOR_PASS_LABEL = "lightblue"
COLOR_PASS_LINE = "blue"
COLOR_UNCLEAR = "#ddd"

alternateColors = {COLOR_FAIL:'#fdd',
                   COLOR_PASS_LABEL:'#ddf',
                   COLOR_UNCLEAR:'#eee'}



#-------- which parameters are we interested in and where do we find them -------
        # logColName["new"] refers to a newer Picarro '(e.g. i2120)
        # logColName["old"] refers to an older Picarro '(e.g. i1015)
parDict = OrderedDict([("H2O",     {"precision":0, "logColName":{"old":"H2O ",              "new":"H2O ",           "newer":"H2O "}}),
                       ("delta18O",{"precision":2, "logColName":{"old":"D_1816 ",           "new":"Delta_18_16 ",   "newer":"Delta_18_16 "}}),
                       ("deltaD",  {"precision":1, "logColName":{"old":"D_DH ",             "new":"Delta_D_H ",     "newer":"Delta_D_H "}}),
                       ("DExcess", {"precision":3, "logColName":{"old":"DEXCESS ",          "new":"DEXCESS ",        "newer":"DEXCESS "}}),
                       ("yEffA",   {"precision":3, "logColName":{"old":"H2O_Y_EFF_A ",      "new":"h2o_y_eff_a ",   "newer":"h2o_vy "}}),                       
                       ("meOH",    {"precision":3, "logColName":{"old":"ORGANIC_MEOH_AMPL ","new":"organic_MeOHampl ","newer":"???"}}),
                       ("CH4",     {"precision":5, "logColName":{"old":"ORGANIC_CH4CONC ",  "new":"organic_ch4conc ", "newer":"CH4 "}})
                       ])
#-------- picarro.log -----------
# except for "valvePeriod", "evaluationPeriod", and "valve", the name fields in the following have to occur within parDict (see above)
# when the name is left without suffix, the value will be the mean of the evaluation period
# when "_sd" is added, the value will be the standard deviation of the respective parameter during the evaluation period
# when "_trend" is added, the value will be the trend of the respective parameter during the evaluation period


#-------- data buffer parameter lists -----------

outPicarroBufferParList=[DataBuffer.Parameter(name = "valvePeriod",      unit = "s"),
                         DataBuffer.Parameter(name = "evaluationPeriod", unit = "s"),
                         DataBuffer.Parameter(name = "valve",            unit = "-"),
                         DataBuffer.Parameter(name = "H2O",              unit = "ppmV"),
                         DataBuffer.Parameter(name = "H2O_sd",           unit = "ppmV"),
                         DataBuffer.Parameter(name = "H2O_trend",        unit = "ppmV"),
                         DataBuffer.Parameter(name = "delta18O",         unit = "per mille"),
                         DataBuffer.Parameter(name = "delta18O_sd",      unit = "per mille"),
                         DataBuffer.Parameter(name = "delta18O_trend",   unit = "per mille"),
                         DataBuffer.Parameter(name = "deltaD",           unit = "per mille"),
                         DataBuffer.Parameter(name = "deltaD_sd",        unit = "per mille"),
                         DataBuffer.Parameter(name = "deltaD_trend",     unit = "per mille"),
                         DataBuffer.Parameter(name = "yEffA",            unit = "???"),
                         DataBuffer.Parameter(name = "meOH",             unit = "???"),
                         DataBuffer.Parameter(name = "CH4",              unit = "???"),
                         DataBuffer.Parameter(name = "DExcess",          unit = "per mille")
                        ]

inPicarroBufferParList = [DataBuffer.Parameter(name = "H2O", unit = "ppmV"),
                          DataBuffer.Parameter(name = "delta18O", unit = "per mille"),
                          DataBuffer.Parameter(name = "deltaD", unit = "per mille"),
                          DataBuffer.Parameter(name = "yEffA", unit = "???"),
                          DataBuffer.Parameter(name = "meOH", unit = "???"),
                          DataBuffer.Parameter(name = "CH4", unit = "???"),
                          DataBuffer.Parameter(name = "DExcess", unit = "per mille")
                        ]

valveBufferPar = DataBuffer.Parameter(name = "ID", unit = "active valve")

#-------- logfile specifications ---------------------------
    #"new" works for a Picarro i2120 or i2130
    #"old" works for a Picarro i1015
logFileSpecsDict = {"old":{'timeFormat':"%m/%d/%y %H:%M:%S.%f", 'colNames':["DATE","TIME"], "nestingDepth":2,
                            'bufferSize': 4000, 'logFileDirFormat':'%Y%m%d', 'fileEnding':"-Data.dat"},
                    "new":{'timeFormat':"%Y-%m-%d %H:%M:%S.%f", 'colNames':["DATE","TIME"], "nestingDepth":4,
                            'bufferSize': 10000, 'logFileDirFormat':'%Y/%m/%d', 'fileEnding':"Z-DataLog_User.dat"},
                    "newer":{'timeFormat':"%Y-%m-%d %H:%M:%S.%f", 'colNames':["DATE","TIME"], "nestingDepth":4,
                            'bufferSize': 10000, 'logFileDirFormat':'%Y/%m/%d', 'fileEnding':"Z-DataLog_User.dat"}}

# complete those specifications with some of the information specified in parDict
for key1 in parDict.keys():    
    for key2 in logFileSpecsDict.keys():        
        logFileSpecsDict[key2]["colNames"].append(parDict[key1]["logColName"][key2])


#=================== helper functions ============================
def correct_notation(text, l=0):
    return "%*s"%(l,text.replace("delta18O",u"\u03B4\u00B9\u2078O [\u2030]").replace("deltaD",u"\u03B4D [\u2030]").replace("H2O",u"H\u2082O [ppmV]").replace("CH4",u"CH\u2084").replace("_mean",""))

def mean(values):
    if len(values)==0:
        return float('nan')
    return(sum(values)/len(values))

def sd(values):
    if len(values)==0:
        return float('nan')
    m = mean(values)
    return(mean(list(map(lambda x: abs(x-m),values))))

def addLists(list1, list2): return [sum(x) for x in zip(list1, list2)]
def multLists(list1, list2): return [x[0]*x[1] for x in zip(list1, list2)]

# this function computes the slope of a list of values
def slope(values):
    ys = values
    xs = range(len(ys))
    m = ((mean(xs)*mean(ys)) - mean(multLists(xs,ys))) / (mean(xs)**2 - mean(multLists(xs,xs)))
    return(m)

# this function computes a "trend" for a list of values
# actually it just compares the mean value of the first half with the mean value of the second half
def trendIndex(values):    
    if len(values)==0:
        return float('nan')
    half = round(len(values)/2)
    return(mean(values[half:]) - mean(values[:half]))

# compute mean, stdDev and trend for each list of values passed with valueListList
def compute_statistics(valueListList, startIndex=None, endIndex=None):
        if startIndex is None: startIndex = 0
        if endIndex is None: endIndex = len(valueListList[0])
        result = {'mean':[], "sd":[], "trend":[]}
        parNames = list(parDict.keys())
        for i,valueList in enumerate(valueListList):
            precision = parDict[parNames[i]]["precision"]
            result['mean'].append(round(mean(valueList[startIndex:endIndex]),precision))
            result['sd'].append(round(sd(valueList[startIndex:endIndex]),precision))
            result['trend'].append(round(trendIndex(valueList[startIndex:endIndex]),precision))
        return result

# format POSIX seconds to a certain time format
def secs2DateString(seconds_POSIX, stringFormat = "%m-%d/%H:%M:%S"):
    return time.strftime(stringFormat,time.gmtime(seconds_POSIX))

# returns the first two columns (seperated by whitespace) of the last line of a file
def get_lastTime(fname, maxLineLength=2000):
    maxLineLength = min([maxLineLength, os.path.getsize(fname)])
    fp=open(fname, "rb")
    try:
        fp.seek(-maxLineLength-1, 2) # 2 means "from the end of the file"
        lastLine = fp.readlines()[-1]
        return ' '.join(map(lambda x: x.decode("utf-8"),lastLine.split()[:2]))
    except:
        return ''

def detect_DeviceVersion(picarroLogDir):
    x = ["dummyValue"]
    devType = "old"

    try: x = os.listdir(picarroLogDir)
    except: pass

    if len(x[-1]) == 4:            
        devType = "new"        

    return devType

def listLogFiles(picarroLogDir, onlyLast = False):

    logFileSpecs = logFileSpecsDict[detect_DeviceVersion(picarroLogDir)]
        
    def get_subEntries(path, currentLevel, fileLevel, onlyLast):            
        try:
            entries = os.listdir(path)            
        except:
            entries=[]
        if len(entries)==0:
            return None

        #print(currentLevel, fileLevel, entries)

        if currentLevel == fileLevel:
            return list(map(lambda x: path+'/'+x, entries))
        else:                
            if onlyLast and currentLevel<fileLevel:                
                entries = [entries[-1]]
            childResults = []
            for entry in entries:
                newEntries = get_subEntries(path+'/'+entry, currentLevel+1, fileLevel, onlyLast)                
                if newEntries is None: continue
                childResults.extend(newEntries)
            return(childResults)

    recResult = get_subEntries(picarroLogDir, 1, logFileSpecs['nestingDepth'], onlyLast)
    recResult = list(filter(lambda x: x.endswith(logFileSpecs['fileEnding']) or
                                      x.endswith(logFileSpecs['fileEnding'] + '.gz'),
                            recResult))
    if onlyLast:
        return recResult[-1]

    return recResult

#=====================================================================================

class PicarroFrame(tk.Frame):
    def __init__(self, master, picarroLogDir, outLogDir, reprocess=False, shortLife = False, firstTimeString = None, *args, **kwargs):
        super(PicarroFrame,self).__init__(master, *args, **kwargs)

        self.picarroLogDir = picarroLogDir
        print("Picarro logdir:", picarroLogDir)
        self.detect_DeviceVersion()
        self.selectionInterval = [None, None]
        self.plotRange = [None,None]
        self.alerted = False
        self.freshMode = True
        self.reprocessMode = reprocess
        self.manager = MeasurementManager.Manager()
        self.managerWindow = None
        
        #----try to load button images--------
        if shortLife:
            self._sequenceButtonImages = [None, None]
        else:
            self._sequenceButtonImages = []
            for name in ["start_32", "pause_32"]:
                try:
                    self._sequenceButtonImages.append(tk.PhotoImage(file="images/"+name+".gif"))
                except:
                    self._sequenceButtonImages.append(None)        

        #------- configuration ------------------
        parameterList = ["firstDay","valveLogFile","plotPars","picarroBufferSize","picarroTimeLag",
                         "dangerThreshold_H2O","flushThreshold_H2O","flushValve","valveTime","evalSeconds",
                         "autoSwitchEnable","autoSwitchCoolDown","critPars","spikeDExcess_cutoffValue"]


        self.conf = configLoader.combine("../config/picarro.cfg", "../config/default/picarro.cfg", parameterList)

        if firstTimeString is None:
            firstTimeString = str(self.conf["firstDay"])
            
        if firstTimeString.startswith('-'):
            now=time.time()
            daysBefore =  - float(firstTimeString)
            self.firstTime = time.time() - 86400 * daysBefore
            print("Starting at %s (%.1f days before now)"%(secs2DateString(self.firstTime+86400,"%Y-%m-%d %H:%M:%S"), daysBefore))
        else:
            self.firstTime = self.str2Time(firstTimeString, "%Y-%m-%d")
            print("Starting at %s"%firstTimeString)
                
                
        #----------------------------------

        
        # create a template for the main data buffer and then copy it twice
        # dataBuffers[1] will constantly be fed with the newest data
        # dataBuffers[0] is for looking at data from the past        
        self._dataBuffer_template = DataBuffer.Buffer(int(self.conf['picarroBufferSize']), None, inPicarroBufferParList, tag="secondary")
        self.dataBuffers = [self._dataBuffer_template.copy(), self._dataBuffer_template.copy()]
        self.dataBuffers[1].tag = "primary"
        
        # this buffer is meant to hold the times and respective names for each valve switch
        self.valveBuffer = DataBuffer.Buffer(10000, None, valveBufferPar)

        valveFilePath = self.conf["valveLogFile"]
        if os.path.isfile(valveFilePath):
            
            print("Reading valve log from \"%s\""%valveFilePath)
            valveFile = open(valveFilePath,"r")                            
            valveDat = valveFile.readlines()           
            
            for splitLine in map(lambda x: x.split('\t'), valveDat[2:]):
                t = datetime.datetime.strptime(splitLine[0], "%Y%m%d%H%M%S")
                t = time.mktime(t.timetuple())
                v = splitLine[1].rstrip()
                try:
                    v = valveDict['valves'][int(v)].name
                except:
                    pass
                self.valveBuffer.add(v,t)
        else:
            print("No valve log found at \"%s\""%valveFilePath)

        if self.reprocessMode:
            bigBuffer = DataBuffer.Buffer(17000, None, inPicarroBufferParList)
            self.load_dataBuffer(dataBuffer = bigBuffer)            
            self.manager.export("../log/picarro_reprocessed.log")
            
        self.open_logFile()

        #------------------- build the GUI ----------------------        

        self.parCanvas = []
        self.parListboxLabel = []
        self.parLabel = []
        self.offsetScales = []
        self.rangeScales = []
        self.meanLabels = []
        self.stdDevLabels = []
        self.trendLabels = []

        self.master.grid_columnconfigure(1, weight=1)
        self.master.grid_rowconfigure(0, weight=1, pad=0)        

        parentFrame = tk.Frame(self)
        parentFrame.grid(sticky='nsew')
        parentFrame.grid_columnconfigure(2, weight=1)

        self.clickStats = None
        self.zoomFactor = 1

        for i, parName in enumerate(self.conf["plotPars"]):            
            x = tk.Frame(parentFrame)
            self.parCanvas.append(PlotCanvas.PlotCanvas(x, plotRangeX=[0,20],plotRangeY=[0,20],
                                                           marginX=60,marginY=17,
                                                           axes=True,bg="white",
                                                           selectionHandler = self.change_selection,
                                                           height=117, width=600))
            
            self.parCanvas[i].grid(row=0,column=0, rowspan=5, sticky='nsew')
            x.grid(row=i,column=0, columnspan=3, sticky='nsew',pady=0)          

            self.parListboxLabel.append(ExtraWidgets.ListboxLabel(x, list(parDict.keys()),i))
            self.parListboxLabel[i].grid(row=0,column=1, sticky = 'we')                                       
            #self.parListboxLabel[i].listbox.bind("<ButtonRelease-1>", lambda event, j = i: self.on_ListboxClick(j))            
            
            tk.Label(x, text='').grid(row=4,column=1) # dummy label for spacing

            self.meanLabels.append(tk.Label(x,  text="mean"))
            self.meanLabels[i].grid(row=1,column=1, sticky = 'we')

            self.stdDevLabels.append(tk.Label(x,  text="stdDev"))
            self.stdDevLabels[i].grid(row=2,column=1, sticky = 'we')

            self.trendLabels.append(tk.Label(x,  text="trend"))
            self.trendLabels[i].grid(row=3,column=1, sticky = 'we')

        self.master.bind('<Left>', lambda e: self.on_arrowPress(True))
        self.master.bind('<Right>', lambda e: self.on_arrowPress(False))
        self.master.bind('<Up>', lambda e: self.on_arrowPress(zoomFactor = 2))
        self.master.bind('<Down>', lambda e: self.on_arrowPress(zoomFactor = 0.5))

        x = tk.Frame(parentFrame)
        x.grid(row=i+1,column=0, columnspan=3, sticky='nsew',pady=0)
        x.grid_columnconfigure(1, weight=1)

        logFiles, startTimes, stopTimes = self.scan_logFiles()
        self.logFileOverview = PlotCanvas.LogFileOverviewCanvas(x, startTimes, stopTimes, self.valveBuffer.get_time(), self.set_plotRange, bg="#aaa")
        self.logFileOverview.grid(row=0,column=1, sticky='nsew')
        self.canvas_tooltip = ExtraWidgets.ToolTip(self.logFileOverview, "Click and select left: overview zoom\nClick and select right: load logged data")

        self.btn_lastView = tk.Button(x, text=u"\u21b5", command = self.logFileOverview.change_selection, font = "Fixedsys 20")
        self.btn_lastView.grid(row=0,column=0, sticky="nsew")
        self.btn_lastView_tooltip = ExtraWidgets.ToolTip(self.btn_lastView, "Show complete overview of all logfiles.")
                
        self.btn_autorefresh = tk.Button(x, text="show newest\ndata",image =self._sequenceButtonImages[1], command = self.set_plotRange)
        self.btn_autorefresh.grid(row=0,column=2, sticky="nsew")
        self.btn_autorefresh_tooltip = ExtraWidgets.ToolTip(self.btn_autorefresh, "...")
        

        self.lastTriggerTime = time.time()
        self.readyToTrigger = False
        self.dangerValves = []

        if shortLife:
            master.destroy()
            return

        self.update()
        self.activeValve = 0
        self.startTime = time.time()        

    def forget_managerWindow(self):
        self.managerWindow = None

    def on_arrowPress(self, backwards = None, zoomFactor = 1):

        duration = self.plotRange[1] - self.plotRange[0]
        if backwards is None:
            offset = 0
        else:
            offset = duration/3 * [1,-1][backwards]
        self.set_plotRange([self.plotRange[1] + offset, self.plotRange[1]-(duration*zoomFactor) + offset])
        

    def on_ListboxClick(self,i):
        n = self.parListboxLabel[i].activeIndex
        parName = self.parListboxLabel[i].activeLabel
        self.conf["plotPars"][i] = parName

    def check_if_within_selection(self, t):
        if self.selectionInterval is None: return False
        if self.selectionInterval[0] is None: return False
        return self.selectionInterval[0] <= t <= self.selectionInterval[1]
               

    def change_selection(self, selectionInterval, button="left"):

        if selectionInterval is None: return        
        try:
            selectionInterval.sort()
        except:
            pass        

        intervalLength = round(selectionInterval[1]-selectionInterval[0])

        # left button interval: set the evaluation period
        if button=="left":
            
            m = None
            x = self.parCanvas[0].getX(selectionInterval[0])
            openManagerWindow = False
                      
            if intervalLength < 20:
                selectionInterval[0] = selectionInterval[1] - self.conf["evalSeconds"]
            evalSeconds = round(selectionInterval[1]-selectionInterval[0])
            self.selectionInterval = selectionInterval.copy()
            self.clickStats = self.compute_recentStatistics(evalSeconds = evalSeconds, stopTime=selectionInterval[1], dataBuffer = self.dataBuffers[self.freshMode])

            
            self.logFileOverview.set_period(selectionInterval, "evalPeriod", "#070")
        
           # if not self.managerWindow is None:
           #     self.managerWindow.update(self.clickStats, m)
                
                            

        if button=="right":
            m = None
            x = self.parCanvas[0].getX(selectionInterval[0])
            openManagerWindow = False
            if intervalLength == 0:                
                m = self.manager.find_measurement(selectionInterval[0])                
                if not m is None:                    
                    selectionInterval = m["interval"]
                    intervalLength = round(selectionInterval[1]-selectionInterval[0])
                    openManagerWindow = True                    
                elif self.managerWindow is None and self.check_if_within_selection(selectionInterval[0]):
                    selectionInterval = self.selectionInterval
                    intervalLength = round(selectionInterval[1]-selectionInterval[0])                    
                    openManagerWindow = True
            if openManagerWindow:
                if self.managerWindow is None:                  
                    self.managerWindow = MeasurementManager.ManagerWindow(self, self.clickStats, x, 0, parDict, self.manager, oldEntry = m)
                else:
                    self.managerWindow.reopen(self.clickStats, oldEntry = m)
            else:
                # current selectionInterval
                self.selectionInterval = None            
                self.update()


    def detect_DeviceVersion(self):
        self.devType = detect_DeviceVersion(self.picarroLogDir)            
        self.logFileSpecs = logFileSpecsDict[self.devType]
            
    
    def listLogFiles(self, onlyLast = False):
        return listLogFiles(self.picarroLogDir, onlyLast)
        

    def scan_logFiles(self):
        logFiles_all = self.listLogFiles()
        # chop the file name in pieces, take the second and third element (date and time) of the last segment of the file name
        logFile_startTimes_all = list(map(lambda x: x.split('/')[-1].split('-')[1:3], logFiles_all))
        # leave date as is and get a standardised time (either take the first 6 digits or add two zeros, if file name only contains four digits)
        logFile_startTimes_all = list(map(lambda x: [x[0], x[1]+'00' if len(x[1])==4 else x[1][:6]],logFile_startTimes_all))
        # now the dates and times can be parsed to an actual time
        logFile_startTimes_all = list(map(lambda x: time.mktime(datetime.datetime.strptime(x[0]+x[1], "%Y%m%d%H%M%S").timetuple()),logFile_startTimes_all))

        logFiles = []
        logFile_startTimes = []
        logFile_stopTimes = []
        
        
        for n,logFile in enumerate(logFiles_all):
            if logFile_startTimes_all[n] < self.firstTime:
                continue
            logFiles.append(logFiles_all[n])
            logFile_startTimes.append(logFile_startTimes_all[n])
            
            t_raw = get_lastTime(logFile)           
            if len(t_raw):                
                t = datetime.datetime.strptime(t_raw, self.logFileSpecs["timeFormat"])                
                logFile_stopTimes.append(time.mktime(t.timetuple()))                
            else:
                logFile_stopTimes.append(logFile_startTimes_all[n]+1)
                #logFile_stopTimes.append(logFile_startTimes_all[n]+3600)

        for n in range(len(logFile_stopTimes)):
            if logFile_stopTimes[n] >= self.firstTime: break

        try:
            self.logFileOverview.startTimes = logFile_startTimes[n:]
            self.logFileOverview.stopTimes = logFile_stopTimes[n:]
        except:
            pass
        
        return logFiles[n:], logFile_startTimes[n:] , logFile_stopTimes[n:]

    def get_valveTimes(self):
        valveTimes = self.valveBuffer.get_time()
        #if len(valveTimes):
        #    self.logFileOverview.valveTimes = valveTimes
        return(valveTimes)
        

    def load_dataBuffer(self, startTime = None, stopTime  = None, dataBuffer = None):       

        if dataBuffer is None:
            dataBuffer = self.dataBuffers[1]

        #dataBuffer_reference = self._dataBuffer_template.copy()

        valveTimes = self.get_valveTimes()
              
        logFiles, logFile_startTimes, logFile_stopTimes = self.scan_logFiles()

        if startTime is None:
            if len(valveTimes):
                startTime = valveTimes[0]
            else:
                startTime = logFile_startTimes[0]

        if stopTime is None:            
            if self.reprocessMode:
                stopTime = valveTimes[-1]
            else:
                stopTime = logFile_stopTimes[-1]

        # find the first logfile that ends after the beginning of the time period of interest        
        for startIndex in range(len(logFile_startTimes)):
            if startTime <= logFile_startTimes[startIndex]: break        
        
        if logFile_startTimes[startIndex] > startTime and startIndex:
            startIndex-=1

        # find the first logfile that ends after the end of the time period of interest       
        for stopIndex in range(startIndex, len(logFile_stopTimes)):
            if stopTime <= logFile_stopTimes[stopIndex]: break        

        # loop over all logfiles, beginning with the last one that started before the first valve period
        self.excludedLines = 0
        self.parsedLines = 0
        for logFile in logFiles[startIndex:(stopIndex+1)]:
            print("processing '"+logFile.split('/')[-1]+"'...")            
            self.open_logFile(logFile)
            for line in self.openFile.readlines():
                parsedLine = self.parse_line(line)               
               
                if len(parsedLine):
                    if parsedLine[0] >= stopTime:
                        break
                    if parsedLine[0] >= startTime:
                        dataBuffer.add(parsedLine[1:], parsedLine[0])
                    self.parsedLines +=1
                else:
                    self.excludedLines += 1
            
            self.compute_bufferStatistics(onlyLast = False, dataBuffer = dataBuffer)

        if self.excludedLines:
            print(self.excludedLines, "of", self.parsedLines+self.excludedLines, "lines were excluded from the analysis")

    def set_plotRange(self, plotRange=None, forcedFreshMode = False):        

        if plotRange is None:
            self.freshMode = not self.freshMode or forcedFreshMode

            if not self.freshMode:
                self.dataBuffers[0] = self.dataBuffers[1].copy()                
           
            t = self.dataBuffers[self.freshMode].get_time()           
            
            self.plotRange[0] = t[-1]-int(self.conf["plotMinutes"])*60
            self.plotRange[1] = t[-1]

        else:

            if plotRange[0] == plotRange[1]:
                plotRange[0] -= int(self.conf["plotMinutes"])*10
                plotRange[1] += int(self.conf["plotMinutes"])*20            
            
            self.freshMode = False
            self.dataBuffers[0] = self._dataBuffer_template.copy()
            plotRange = sorted(plotRange)
            self.load_dataBuffer(startTime = plotRange[0], stopTime  = plotRange[1], dataBuffer = self.dataBuffers[0])           

            t = self.dataBuffers[self.freshMode].get_time()          
                        
            self.plotRange[0] = t[0]
            self.plotRange[1] = t[-1]           

        self.btn_autorefresh.config(image=self._sequenceButtonImages[int(self.freshMode)])
        self.btn_autorefresh_tooltip.text = ["Show freshest data","Freeze data plot"][int(self.freshMode)]
                

    def get_mostRecentLogFile(self):
        return(self.listLogFiles(onlyLast=True))
        

    def try_index(self, header, searchWord):
        try:
            result = header.index(searchWord)
        except:
            result = None
        return result

    def try_parse(self, line, index):
        if not index is None:
            try:
                return float(line[index : index+25].rstrip())
            except:
                pass
        return float('nan')
        

    def open_logFile(self, filepath = None):
        if filepath is None:
            self.activeLogFile = self.get_mostRecentLogFile()            
        else:
            self.activeLogFile = filepath
            
        if not self.activeLogFile is None:
            try:
                self.openFile.close()
            except:
                pass            
            
            if self.activeLogFile.endswith(".gz"):
                import gzip
                tempfile = open("temp.dat",'wb')
                tempfile.write(gzip.open(self.activeLogFile, 'rb').read())
                tempfile.close()                
                self.openFile = open("temp.dat", 'r')
            else:
                self.openFile = open(self.activeLogFile, 'r')

            self.logFileHeader = self.openFile.readline()            

            self.parIndices = list(map(lambda x: self.try_index(self.logFileHeader,x), self.logFileSpecs["colNames"]))
            for i in self.parIndices:
                if i is None and self.devType == "new":
                    self.devType = "newer"
            if self.devType == "newer":
                self.logFileSpecs = logFileSpecsDict[self.devType]
                self.parIndices = list(map(lambda x: self.try_index(self.logFileHeader,x), self.logFileSpecs["colNames"]))

    def str2Time(self, s, f="%Y-%m-%d %H:%M:%S.%f"):       
        t = datetime.datetime.strptime(s, f)
        return(time.mktime(t.timetuple()))

    def parse_line(self,line):       

        if len(line) < len(self.logFileHeader):
            return[]        
        
        try:
            dateString = line[self.parIndices[0] : self.parIndices[0]+25].rstrip()
            timeString = line[self.parIndices[1] : self.parIndices[1]+25].rstrip()
            t = self.str2Time(dateString + ' ' + timeString, self.logFileSpecs["timeFormat"])
            
            
            r =[t -  self.conf["picarroTimeLag"]*3600]           

            for n,parName in enumerate(parDict.keys()):
                if self.parIndices[n+2] is None:
                    r.append(0)
                else:
                    r.append(self.try_parse(line, self.parIndices[n+2]))

            # add DExcess
            r[-1] = r[3] - r[2]*8

            if r[-1] > self.conf["spikeDExcess_cutoffValue"]:
                #print(r[1], " D-Excess cutoff value (%.0f[\u2030]) exceeded, values discarded"% self.conf["spikeDExcess_cutoffValue"])
                return []
                                     
        except:
            return[]

        return(r)

    def reset_trigger(self, activeValve=None):        
        self.lastTriggerTime = time.time()
        self.readyToTrigger = False

        if not activeValve is None:
            self.activeValve = activeValve
            self.valveBuffer.add(activeValve, self.lastTriggerTime)        
            self.compute_bufferStatistics(onlyLast = False, startTime = self.startTime)
            self.manager.export("../log/picarro%s.log"%secs2DateString(self.startTime, "%Y%m%d%H%M%S"))
            

    def isAllFine(self, stats):
        allFine = True
        for parName in self.conf["critPars"].keys():       
            i = list(parDict.keys()).index(parName)
            fine_stdDev = stats['sd'][i] <= self.conf["critPars"][parName]["sd"]
            fine_trend = abs(stats['trend'][i]) <= self.conf["critPars"][parName]["trend"]
            allFine = allFine and fine_stdDev and fine_trend
        return allFine        
        
            

    def compute_bufferStatistics(self, onlyLast=True, dataBuffer = None, startTime=0):

        if dataBuffer is None:
            dataBuffer = self.dataBuffers[1]

        if not len(dataBuffer.dataBuffer):            
            return

        valve_t = self.valveBuffer.get_time()
        valves = self.valveBuffer["ID"]
        data_t = dataBuffer.get_time()
        #dat = dataBuffer.get_data()

        if len(valves) < 2 or len(data_t) < 2: return

        if onlyLast: startIndex = len(valve_t)-1
        else: startIndex = 1

        temp_managerWindow = None
        
        for i in range(startIndex,len(valve_t)):            
            if valve_t[i] < startTime: continue
            if valve_t[i] < data_t[0]: continue
            if valve_t[i] > data_t[-1]:break
            if (valve_t[i] - valve_t[i-1]) < self.conf['valveTime']: continue

            for offset in range(10,-1,-1):
                clickStats = self.compute_recentStatistics(stopTime=valve_t[i]-offset, dataBuffer = dataBuffer)
                if not clickStats is None:
                    if clickStats['fine']: break
            
            if clickStats is None:
                continue
            if temp_managerWindow is None:
                temp_managerWindow = MeasurementManager.ManagerWindow(self, clickStats, -1000, -1000, parDict, self.manager)
                
            temp_managerWindow.create_entry(clickStats, ID = valves[i-1], sampleType = "inSitu")

        if not temp_managerWindow is None: temp_managerWindow.destroy()       
               
       

    def compute_recentStatistics(self, evalSeconds = None, stopTime = None, dataBuffer = None):
        if evalSeconds is None:
            evalSeconds = self.conf['evalSeconds']       

        t = dataBuffer.get_time()       

        if stopTime is None:
            stopTime = t[-1]
        
        skipCount = 0
        for evalIndex in range(len(t)-1,0,-1):
            if t[evalIndex] > stopTime:
                skipCount+=1
            if (stopTime - t[evalIndex]) > evalSeconds: break

        if (stopTime - t[evalIndex]) > (evalSeconds+10):
            return None

        evalIndex +=1

        result = {}
        allFine = True

        for parName in parDict.keys():           
            
            par = dataBuffer.get_data(parameter=parName, startIndex=evalIndex)[0]

            #print(par)
            
            if skipCount: par = par[:-skipCount]                       

            stdDev = sd(par)
            trend = trendIndex(par)

            try:
                fine_stdDev = stdDev <= self.conf["critPars"][parName]["sd"]
                fine_trend = abs(trend) <= self.conf["critPars"][parName]["trend"]
                allFine = allFine and fine_stdDev and fine_trend

                if fine_stdDev and fine_trend:
                    colors = [COLOR_PASS_LINE,  COLOR_PASS_LABEL,  COLOR_PASS_LABEL]
                else:
                    colors = [COLOR_FAIL for x in range(3)]
                    if fine_stdDev: colors[1] = COLOR_PASS_LABEL
                    if fine_trend: colors[2] = COLOR_PASS_LABEL
            except:
                colors = [COLOR_UNCLEAR for x in range(3)]

            result[parName] = {'mean': round(mean(par),parDict[parName]["precision"]),
                               'sd': round(stdDev,parDict[parName]["precision"]),
                               'trend': round(trend,parDict[parName]["precision"]),
                               'colors': colors}

        result['info'] = {'date': time.strftime("%Y-%m-%d",time.gmtime(t[evalIndex])),
                          'time': time.strftime("%H:%M:%S",time.gmtime(stopTime)),
                          'duration': round(stopTime-t[evalIndex]),
                          'evalIndex':evalIndex,
                          'interval':[t[evalIndex],stopTime]}

        result['fine'] = allFine        
        return(result)

    def get_plotIndices(self,t):       
        for plotEnd in range(len(t)-1,0,-1):
            if (t[plotEnd]) < self.plotRange[1]: break
        for plotStart in range(plotEnd,0,-1):
            if (t[plotStart]) < self.plotRange[0]: break

        if plotStart==plotEnd:
            if plotEnd == 0: plotEnd = 1
            if plotStart == (len(t)-1): plotStart = len(t)-2

        return plotStart, plotEnd+1

    def check_dangerThreshold(self, value, lastValve):
        if value >= self.conf['dangerThreshold_H2O']:
            dangerValve = lastValve
            if not dangerValve in self.dangerValves and dangerValve != self.conf['flushValve']:
                self.dangerValves.append(dangerValve)
                self.alerted = True
            else:
                self.alerted = False

    def isFlushedDry(self):
        H2O = self.dataBuffers[self.freshMode]["H2O"][0][-1]
        return H2O <= self.conf["flushThreshold_H2O"]

    def update_primaryDataBuffer(self):
        # get most recent data from log file
        mostRecent = self.get_mostRecentLogFile()        

        if mostRecent is None:
            for i in range(len(self.pars)):
                self.parCanvas[i].create_text(580, 50, text="failed to read log file", font = tkFont.Font(size=20))
            return
            
        if mostRecent != self.activeLogFile:
            self.open_logFile()

        wait = False
        while not wait:
            where = self.openFile.tell()
            line = self.openFile.readline()
            if not line:
                self.openFile.seek(where)
                wait = True
            else:
                parsedLine = self.parse_line(line)                
                if len(parsedLine):
                    self.dataBuffers[1].add(parsedLine[1:], parsedLine[0])
        

    def update(self):

        self.update_primaryDataBuffer()       

        t = self.dataBuffers[self.freshMode].get_time()
        if not len(t): return

        if self.plotRange[0] is None:
            self.set_plotRange(forcedFreshMode=True)

        if self.freshMode:
            self.plotRange[0] = t[-1] - self.conf["plotMinutes"]*60
            self.plotRange[1] = t[-1]
                    

        self.logFileOverview.set_period([t[0],t[-1]], "bufferPeriod", "#f33",8)
        self.logFileOverview.set_period(self.plotRange, "plotPeriod", "#3aa",4)

        if self.selectionInterval is None:
                self.logFileOverview.delete("evalPeriod") 

        plotStart, plotEnd = self.get_plotIndices(t)
            
        # compute statistics for evaluation of most recent data
        recentStatistics = self.compute_recentStatistics(dataBuffer = self.dataBuffers[1])
        if recentStatistics is None:
            self.after(500, self.update)
            return
        evalIndex = recentStatistics["info"]["evalIndex"]

        # prepare some plot stuff wich is the same for all plots
        lastValve = "???"
        valve_t = []
        if len(self.valveBuffer.dataBuffer)>1:            
            valve_t = self.valveBuffer.get_time()            
            valve_plotStart, valve_plotEnd = self. get_plotIndices(valve_t)
            valve_tPlot = valve_t[valve_plotStart:valve_plotEnd]
            valve_labels = self.valveBuffer["ID"]
            last_valve = valve_labels[-1]
            valve_labels = valve_labels[valve_plotStart:valve_plotEnd]

        intervals = self.manager.get_intervals(self.plotRange)        
        
        # make a plot for each parameter        
        for n,parName in enumerate(self.conf["plotPars"]):
        #for n in range(len(self.conf["plotPars"])):
         #   parName =

            parName = self.parListboxLabel[n].activeLabel
            i = self.parListboxLabel[n].activeIndex
                    
            i = list(parDict.keys()).index(parName)
            
            plot = self.parCanvas[n] 

            if len(intervals):
                x0=[]; x1=[]; xLab = []; col=[]; labels = []
                for interval in intervals:                    
                    x = [interval["interval"][0], interval["interval"][1]]
                    x0.append(x[0])
                    x1.append(x[1])
                    xLab.append(x[0]+(x[1]-x[0])/2)
                    col.append(alternateColors[interval["data"]["colors"][parName]])                    
                    labels.append(interval["data"]["ID"])
                plot.vertBoxes(x0,x1,color = col, tag="intervalBoxes")
                plot.relativeLabel(xLab,[1 for x in range(len(xLab))], labels, color = "#555", tag="intervalLabels")
            else:
                plot.delete("intervalBoxes")
                plot.delete("intervalLabels")

            # check for danger threshold exceedance
            parValues = self.dataBuffers[self.freshMode][parName]
            
            if parName == "H2O" and self.freshMode:
                self.check_dangerThreshold(parValues[-1], lastValve)

            plot.draw_xAxis([t[plotStart],t[plotEnd]],optimalTicks = 10)
            plotParValues = parValues[plotStart:plotEnd].copy()
            plot.draw_yAxis([min(plotParValues),max(plotParValues)], parDict[parName]["precision"], optimalTicks = 5)
            plot.plotData(t[plotStart:plotEnd], plotParValues, tag="long", color = COLOR_PLOTLINE)            

            # plot valve switch indicators
            if len(valve_t):
                plot.vertLines(valve_tPlot, valve_labels, tag = "valveLabels", color="#aaa")                
                
            # get colors from recentStatistics
            colors = recentStatistics[parName]['colors']

            # plot the evaluated selection of the parameters time series
            if self.freshMode:
                plot.plotData(t[evalIndex:], parValues[evalIndex:], "short",colors[0], 2)
            else:
                plot.delete("short")
                

            # to be explained...
            if self.selectionInterval is None or self.selectionInterval[0] is None or self.clickStats is None:
                plot.delete("evalPeriod")                
            else:
                try:
                    color = {"red":"#faa", "blue": "#aaf"}[self.clickStats[parName]['colors'][0]]
                except:
                    color = COLOR_UNCLEAR
                    
                plot.vertLines(self.selectionInterval, tag = "evalPeriod", color=color, width=2)                

                meanVal = self.clickStats[parName]['mean']
                sdVal = self.clickStats[parName]['sd']
                trendVal = self.clickStats[parName]['trend']                
                baseRelY = [0.25,0.75][meanVal < (plot.plotRangeY[0] + plot.plotRangeY[1])/2]
                if trendVal > 0:
                    trendChar = u'\u2197'
                else:
                    trendChar = u'\u2198'
                    trendVal = -trendVal

                duration = self.selectionInterval[1] - self.selectionInterval[0]
                x = self.selectionInterval[0] + duration/2
                
                plot.relativeLabel(x, baseRelY+0.15, '%s: %.*f'%(u'\u03bc', parDict[parName]["precision"], meanVal),  tag = ("evalPeriod", "mean"), color="#000")
                plot.relativeLabel(x, baseRelY+0.05,     '%s: %.*f'%(u'\u03c3', parDict[parName]["precision"], sdVal),    tag = ("evalPeriod","sd"),    color="#000")
                plot.relativeLabel(x, baseRelY-0.05, '%s: %.*f'%(trendChar, parDict[parName]["precision"], trendVal), tag = ("evalPeriod","slope"), color="#000")
                plot.relativeLabel(x, baseRelY-0.15, '%s: %.0fs'%('t',                                    duration),  tag = ("evalPeriod", "duration"), color="#000")            
            

            # plot the recentStatitics values for the current parameter 
            self.meanLabels[n].config(text="%5s: %.*f"%(u'\u03bc',parDict[parName]["precision"],recentStatistics[parName]['mean']))
            self.stdDevLabels[n].config(text="%5s: %.*f"%(u'\u03c3',parDict[parName]["precision"],recentStatistics[parName]['sd']), bg=colors[1])
            self.trendLabels[n].config(text="%5s: %.*f"%("trend",parDict[parName]["precision"],recentStatistics[parName]['trend']), bg=colors[2])


        self.readyToTrigger =  self.conf['autoSwitchEnable'] and ((time.time() - self.lastTriggerTime) > self.conf['autoSwitchCoolDown']) and recentStatistics["fine"]
        #self.readyToTrigger = False
        self.after(500, self.update)

    def on_resize(self,event):
        width = self.master.winfo_width()
        height = self.master.winfo_height()
        for i in range(len(self.conf["plotPars"])):
            self.parCanvas[i].on_resize(width-90,(height-50)/len(self.conf["plotPars"])-6)
        self.logFileOverview.on_resize(width-83,50)
        

if __name__ == "__main__":

    args = []
    for arg in sys.argv:
        args.append(arg)    

    def on_resize(event):
        p.on_resize(event)    

    root = tk.Tk()
    root.title("Picarro")
    root.geometry("%dx%d+%d+%d"%(1280,500,1,0))
    p = PicarroFrame(root, logDir, "./picarro.log", relief=tk.RAISED,
                     reprocess = "reprocess" in args or True,
                     shortLife = "shortLife" in args,
                     firstTimeString = firstTimeString)
    try:
        p.pack(fill = tk.BOTH, expand=True)
        p.bind("<Configure>", on_resize)
        root.mainloop()
    except:
        pass
