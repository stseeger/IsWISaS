import tkinter as tk
from tkinter import ttk
from tkinter import font as tkFont
import datetime
import time
import os
from collections import OrderedDict
import calendar
from tkinter.filedialog import asksaveasfilename as tkAsksaveasfilename

#-------------
import configLoader
import ExtraWidgets

def correct_notation(text, l=0):
    return "%*s"%(l,text.replace("delta18O",u"\u03B4\u00B9\u2078O [\u2030]").replace("deltaD",u"\u03B4D [\u2030]").replace("H2O",u"H\u2082O [ppmV]").replace("CH4",u"CH\u2084").replace("_mean",""))

def secs2DateString(seconds_POSIX, stringFormat = "%m-%d/%H:%M:%S"):
    return time.strftime(stringFormat,time.gmtime(seconds_POSIX))

labelFont = "Fixedsys 10"

class Manager():
    def __init__(self):
        self.measurements = {}
        self.idInfo = {}
        self.intervals = [[],[]]

                #--- load config file ----------
        #self.conf = configLoader.load_confDict("../config/logEntries.cfg")

        parameterList = ["output_columns","sampleTypes"]

        self.conf = configLoader.combine("../config/logEntries.cfg", "../config/default/logEntries.cfg", parameterList)
        
        self.conf["sampleTypes"]["inSitu"]=[[''],['']]
        self.generalEntries = ['ID','notes']
        
        idEntries = []
        sampleEntries=['ID']

        # now loop over all sample types and add additional parameters
        # for idEntries and sampleEntries, in case they have not yet
        # been added due to earlier occurence in another sample type
        for key, sampleType in self.conf["sampleTypes"].items():            
            for idEntry in sampleType[0]:
                if not idEntry in idEntries:
                    if len(idEntry):
                        idEntries.append(idEntry)
            for sampleEntry in sampleType[1]:
                if not sampleEntry in sampleEntries:
                    if len(sampleEntry):
                        sampleEntries.append(sampleEntry)        

        # loop over all output columns (which are mandatory for all sample types)
        # in case the first subentry is empty, this means, the parameter
        # is not expected to be found in clickStats and has to be entered manually
        for entry in self.conf["output_columns"]:            
            if not len(entry[0]):
                sampleEntries.append(entry[1])
                self.generalEntries.append(entry[1])

        # add notes to both entries
        idEntries.append('notes')
        sampleEntries.append('notes')
        self.entryDict = {'sample': sampleEntries, 'id': idEntries}        

        self.outCols = self.entryDict['sample'].copy() + list(map(lambda x: x[1],filter(lambda x: x[0]!="",self.conf["output_columns"])))
        self.outCols.pop(self.outCols.index("notes"))
        self.outCols.append("notes")

    def load_from_file(self, filepath):
        pass

    def check_ID(self,ID):
        if ID in self.idInfo.keys():
            return self.idInfo[ID]
        return None

    def check_directions(self, timeStamp):
        timeStamps = self.measurements.keys()
        if not len(timeStamps):
            return False, False
        
        return (min(timeStamps) < timeStamp), (max(timeStamps) > timeStamp)

    def go_to(self, timeStamp, new_timeStamp, forward):
        timeStamps = list(self.measurements.keys())

        if not new_timeStamp is None:
            timeStamps += [new_timeStamp]

        timeStamps = sorted(timeStamps)
        if forward:
            destination = list(filter(lambda ts: ts > timeStamp, timeStamps))[0]
        else:
            destination = list(filter(lambda ts: ts < timeStamp, timeStamps))[-1]

        if destination in self.measurements.keys():
            return self.measurements[destination].copy()
        else:
            return None

    def find_measurement(self, t):
        if len(self.measurements):
            for key, entry in self.measurements.items():
                if entry["interval"][0] < t < entry["interval"][1]:
                    return entry
        return None

    def update_intervals(self):
        self.intervals=[[],[],[]]
        for key, entry in self.measurements.items():
            self.intervals[0].append(entry['interval'][0])
            self.intervals[1].append(entry['interval'][1])
            self.intervals[2].append(entry['data']['ID'])

    def get_intervals(self, timeRange):

        if len(self.intervals[0])<1: return []
        
        for iStart, val in enumerate(self.intervals[0]):
            if val > timeRange[0]: break

        for iStop, val in enumerate(self.intervals[1][iStart:]):
            if val > timeRange[1]: break

        iStop += iStart+1

        timeStamps = list(self.measurements.keys())[iStart:iStop]

        intervals = []
        for n,timeStamp in enumerate(timeStamps):
            intervals.append(self.measurements[timeStamp])           

        return intervals
            
            
        
    def add(self, sampleInfo, idInfo):
        # add ID info
        self.idInfo[sampleInfo['ID']] = idInfo

        t = calendar.timegm(datetime.datetime.strptime(sampleInfo["time"], "%Y-%m-%d %H:%M:%S").timetuple())
        self.measurements[sampleInfo["time"]] = {"data":sampleInfo, "interval":[t-sampleInfo["duration [s]"],t]}

        self.update_intervals()

    def remove(self,timeStamp):
        self.measurements.pop(timeStamp)
        self.update_intervals()

    def export(self, path, appendMode = False):       
        
        timeStamps = sorted(self.measurements.keys())
        sampleTypes = OrderedDict()
        dataLines = [['time (UTC)', 'duration [s]'] + self.outCols]
        IDs = []
        for timeStamp in timeStamps:
            dataLine=[]
            # while already running thorugh all measurements, the following lines
            # keep track of the actually occuring sample types
            ID = self.measurements[timeStamp]["data"]["ID"]
            if ID not in IDs:
                IDs.append(ID)
                idInfo = self.idInfo[ID]
                sampleType = idInfo["type"]
                if not sampleType in sampleTypes:
                    sampleTypes[sampleType] = []
                sampleTypes[sampleType].append([ID,idInfo])
            
            # the following code block collects all measurement data and
            # keeps them in the list "dataLines"
            appendNotes = False
            for key in self.measurements[timeStamp]["data"].keys():
                if key == "colors": continue
                if key == "notes":
                    appendNotes = True
                    continue
                dataLine.append(self.measurements[timeStamp]["data"][key])
            if appendNotes:
                dataLine.append(self.measurements[timeStamp]["data"]["notes"])
            dataLines.append(dataLine)

        metaBlock = []       
        for sampleType in sampleTypes.keys():            
            oneTypeData = sampleTypes[sampleType]
            neededEntries = self.conf["sampleTypes"][sampleType][0].copy()
            neededEntries.append("notes")
            neededEntries = list(filter(lambda x: len(x)>0, neededEntries))
            metaLines = [['#sampleType', sampleType, 'ID'] + neededEntries.copy()]
            for thing in oneTypeData:
                metaLine=['#sampleType', sampleType, thing[0]]               
                for subKey in neededEntries:
                    metaLine.append(thing[1][subKey])
                metaLines.append(metaLine)                            
            metaBlock.append(metaLines)

        if os.path.exists(path) and False:
            oldLines = open(path, 'r').readlines()
            print(oldLines)
            oldMetaLines = list(filter(lambda x: x.startswith('#'), oldLines))
            oldDataLines = list(filter(lambda x: not x.startswith('#'), oldLines))
        else:
            oldMetaLines = []
            oldDataLines = []


        writtenLines = []
        with open(path, 'w') as outFile:

            for line in oldMetaLines:
                outFile.write(line)
                writtenLines.append(line)

            for sampleType in metaBlock:
                for line in sampleType:
                    newLine = '\t'.join(line)+'\n'
                    if newLine in writtenLines: continue
                    outFile.write(newLine)
                outFile.write('#\n')
                            
            for line in oldDataLines:
                outFile.write(line)
                writtenLines.append(line)
                
            for line in dataLines:
                newLine = '\t'.join(map(lambda x: str(x),line))+'\n'
                if newLine in writtenLines: continue
                outFile.write(newLine)

           
##################################################################        

class ManagerWindow(tk.Toplevel):
    def __init__(self, master, clickStats, x, y, parDict, manager, oldEntry = None):
        super(ManagerWindow, self).__init__()
        self.wm_title("Measurement details")

        self.master = master
        parNames = parDict.keys()
        self.parDict = parDict
        
        try:
            self.new_clickStats = clickStats.copy()
            self.active_clickStats = clickStats.copy()
        except:
            self.new_clickStats = None
            self.active_clickStats = None
            

        self.manager = manager       

        self.measurements = []       


        self.entryHolder = {"sample":[], "id":[]}
        #-----ID information frame---------------------        
        idFrame = tk.LabelFrame(self, text="ID information", font=labelFont, height=100)
        idFrame.grid(row=0,column=1, sticky='we')

        self.typeList = list(self.manager.conf["sampleTypes"].keys())

        tk.Label(idFrame,text="%-20s"%"type", font=labelFont, justify=tk.LEFT).grid(row=0,column=0,sticky='we')

        self.typeLabel = ExtraWidgets.ListboxLabel(idFrame,self.typeList, 0, font=labelFont)
        self.typeLabel.grid(row=0, column=1, sticky='we')
        self.typeLabel.listbox.bind("<ButtonRelease-1>", self.change_sampleType, add='+')
        self.typeLabel.listbox.bind("<KeyRelease-Return>", self.change_sampleType, add='+')

        for n,entry in enumerate(self.manager.entryDict["id"]):
            l = tk.Label(idFrame,text="%-20s"%entry, font=labelFont, justify=tk.LEFT)
            l.grid(row=n+1, column=0,sticky='we')
            e = tk.Entry(idFrame)
            e.grid(row=n+1, column=1,sticky='we')            
            self.entryHolder["id"].append([e,l])

        self.btnID = tk.Button(idFrame, text="Change ID information", state=tk.DISABLED,command = self.change_idEntry)
        self.btnID.grid(row=n+2, column=0, columnspan=2, sticky="nsew")   
        
        #------Sample information frame-------------------        
        sampleFrame = tk.LabelFrame(self, text="Sample information", font=labelFont, height=100)
        sampleFrame.grid(row=1,column=1, sticky='nsew')        

        for n, entry in enumerate(self.manager.entryDict['sample']):
            l = tk.Label(sampleFrame,text="%-20s"%entry, font=labelFont, justify=tk.LEFT)
            l.grid(row=n, column=0, sticky='nsew')
            e = tk.Entry(sampleFrame)
            e.grid(row=n, column=1)
            if entry == "ID":
                e.bind("<ButtonRelease-1>", self.on_change_ID)
                e.bind("<KeyRelease>", self.on_change_ID)
            self.entryHolder["sample"].append([e,l])

        self.btnAdd = tk.Button(sampleFrame, text="Add Entry", state=tk.DISABLED, command = self.create_entry)
        self.btnAdd.grid(row=n+1, column=0, columnspan=2, sticky="nsew")

        self.btnRemove = tk.Button(sampleFrame, text="Remove Entry",command = self.remove_entry)
        self.btnRemove.grid(row=n+1, column=0, sticky="nsew")
        self.btnRemove.grid_remove()
        
        self.btnChange = tk.Button(sampleFrame, text="Change Entry",command = self.create_entry)
        self.btnChange.grid(row=n+1, column=1, sticky="nsew")
        self.btnChange.grid_remove()

        self.countLabel = tk.Label(sampleFrame, text='---', font=labelFont, fg='#666')
        self.countLabel.grid(row=n+2, columnspan=2, sticky="nsew")
        
        #------Measurement data frame-------------------
        dataFrame = tk.LabelFrame(self, text="Picarro measurement", font=labelFont)
        dataFrame.grid(row=0,column=0,rowspan=2, sticky='nsew')

        self.dataLabelList = []

        f = tk.LabelFrame(dataFrame, text="time", font=labelFont)
        f.grid(row=0, columnspan=2, sticky='nsew')

        for n,item in enumerate([["date","date"], ["time","stop time"], ["duration","duration [s]"]]):
            tk.Label(f, text="%-14s:"%item[1], font=labelFont).grid(row=n)
            self.dataLabelList.append([["info",item[0]], "%10s",
                                       tk.Label(f,"", font=labelFont)])
            self.dataLabelList[n][2].grid(row=n,column=2, sticky='nsew')


        
        for k,key in enumerate(clickStats.keys()):
            if not isinstance(clickStats[key], dict) or key=="info": continue
            subKeys = clickStats[key].keys()
            f = tk.LabelFrame(dataFrame, text=correct_notation(key,-17), font=labelFont)
            f.grid(row=k+1, columnspan=2, sticky='nsew')
            for s,subKey in enumerate(subKeys):
                if subKey in ["colors"]: continue
                if key in ["yEffA","meOH","CH4"] and subKey in ["sd","trend"]: continue
                tk.Label(f, text="%-14s:"%subKey, font=labelFont).grid(row=s)
                self.dataLabelList.append([[key,subKey], "%%8.%df"%self.parDict[key]["precision"],
                                           tk.Label(f,"", font=labelFont)])
                self.dataLabelList[len(self.dataLabelList)-1][2].grid(row=s, column=2)
        #-------------------------

        self.btn_prev = tk.Button(dataFrame, text="<===", command = lambda x=0: self.go_to(False), font = labelFont)
        self.btn_prev.grid(row=k+1, column=0,sticky="nsew")
        
        self.btn_next = tk.Button(dataFrame, text="===>", command = lambda x=0: self.go_to(True), font = labelFont)
        self.btn_next.grid(row=k+1, column=1,sticky="nsew")

        self.btn_save = tk.Button(self, text="Export to csv-file", state=tk.DISABLED, command = self.export, font = labelFont)
        self.btn_save.grid(row=2,columnspan=2, sticky='nsew')

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        #----------
        self.update(clickStats, oldEntry)
        self.change_sampleType()
        self.check_directions()
        self.wm_attributes("-topmost", 1)

        self.bind("<Destroy>", self.clean_up, add='+')

        #-------------
        self.after(1,lambda x=x, y=y: self.adjust_position(x,y))

    def adjust_position(self,x,y):
        w=self.winfo_width()
        h=self.winfo_height()
        if x < w: x=x+w+50
        else:     x=x-50
        self.geometry("%dx%d+%d+%d"%(w,h,x-w,y))
        

    def get_timeStamp(self, clickStats=None):
        if clickStats is None:
            clickStats = self.active_clickStats
        return clickStats["info"]["date"]+' '+clickStats["info"]["time"]
        
    def clean_up(self,event):        
        self.master.forget_managerWindow()        

    def reopen(self, clickStats, oldEntry = None):
        self.btnAdd.configure(state = tk.DISABLED)
        self.active_clickStats = clickStats.copy()
        if oldEntry is None:
            self.new_clickStats = self.active_clickStats.copy()
                        
        self.update(clickStats, oldEntry)
        self.check_directions()
        self.lift()

    def update(self, clickStats, oldEntry = None):
        if clickStats is None:
            self.active_clickStats = None
        else:
            self.active_clickStats = clickStats.copy()
        if oldEntry is None:
            self.new_clickStats = clickStats.copy()
        
        # update measurement data labels
        for item in self.dataLabelList:
            keys = item[0]
            formatStr = item[1]            
            label = item[2]
            value = clickStats[keys[0]]            
            for n in range(1,len(keys)):
                value = value[keys[n]]            
            label.configure(text=formatStr%value)
            
        # update sample information data
        for n, key in enumerate(self.manager.entryDict['sample']):                
            self.entryHolder["sample"][n][0].delete(0,tk.END)
            if not oldEntry is None:
                self.entryHolder["sample"][n][0].insert(0,oldEntry["data"][key])

        # update ID information data
        #  first delete everything
        for n, entry in enumerate(self.manager.entryDict['id']):
            self.entryHolder['id'][n][0].delete(0, tk.END)
        # then fill with data if possible
        if not oldEntry is None:
            idInfo = self.manager.idInfo[oldEntry["data"]["ID"]]
            self.change_sampleType(newType = self.manager.idInfo[oldEntry["data"]["ID"]]['type'])
            idInfo = self.manager.idInfo[oldEntry["data"]["ID"]]
            for n, entry in enumerate(self.manager.entryDict['id']):
                self.entryHolder['id'][n][0].insert(0, idInfo[entry])
                
        # update button states
        if oldEntry is None:
            self.btnAdd.grid()
            self.btnChange.grid_remove()
            self.btnRemove.grid_remove()
        else:
            self.btnAdd.grid_remove()
            self.btnChange.grid()
            self.btnRemove.grid()

        count = len(self.manager.measurements)
        self.check_directions()
        if oldEntry is None:
            labelText = "new sample"
        else:
            number = list(sorted(self.manager.measurements.keys())).index(oldEntry["data"]["time"])+1
            labelText = "sample %2d/%d"%(number,count)

        self.btn_save.configure(state = [tk.DISABLED, tk.NORMAL][count>0])
            
            
        self.countLabel.configure(text = labelText)
            

    def change_idEntry(self):
        newEntry = self.build_idEntry()
        self.manager.idInfo[ID] = newEntry
            

    def on_change_ID(self,event):
        ID = self.entryHolder["sample"][0][0].get()
        state = [tk.DISABLED, tk.NORMAL][len(ID)>0]
        self.btnAdd.configure(state = state)
        self.btnID.configure(state = state)

        idInfo = self.manager.check_ID(ID)
        if idInfo is None: return

        for n, entry in enumerate(self.manager.entryDict['id']):
            self.entryHolder['id'][n][0].delete(0, tk.END)
            self.entryHolder['id'][n][0].insert(0, idInfo[entry])

    def check_directions(self):
        backwards, forwards = self.manager.check_directions(self.get_timeStamp())        
        stateOptions = [tk.DISABLED, tk.NORMAL]        
        self.btn_prev.configure(state=stateOptions[backwards])
        self.btn_next.configure(state=stateOptions[forwards])

    def go_to(self, go_forward):
        selEntry = self.manager.go_to(self.get_timeStamp(), self.get_timeStamp(self.new_clickStats), go_forward)
        
        if selEntry is None:           
            self.master.change_selection(self.new_clickStats["info"]["interval"])
            self.active_clickStats = self.new_clickStats.copy()
        else:
            self.master.change_selection(selEntry["interval"])
            self.active_clickStats = self.master.clickStats.copy()
                            
        self.update(self.active_clickStats, selEntry)

    def build_idEntry(self):
        result = OrderedDict()
        result["type"] = self.typeLabel.activeLabel
        for n, entry in enumerate(self.manager.entryDict['id']):
            result[entry] = self.entryHolder['id'][n][0].get()

    def remove_entry(self):
        self.manager.remove(self.get_timeStamp())
        self.destroy()   

    def create_entry(self, clickStats = None, ID = None, sampleType=None):

        if clickStats is None:
            clickStats = self.new_clickStats
        else:
            self.new_clickStats = clickStats

        if sampleType is None:
            sampleType = list(self.manager.conf["sampleTypes"].keys())[0]

        # compile sample specific information
        sampleInfo = OrderedDict()
        sampleInfo['time'] = self.get_timeStamp(self.new_clickStats)
        sampleInfo['duration [s]'] = self.new_clickStats['info']['duration']
        for n, entry in enumerate(self.manager.entryDict['sample']):
            sampleInfo[entry] = self.entryHolder['sample'][n][0].get()


        sampleInfo["colors"] = {}
        
        # compile infomation from fields clickStats
        for entry in self.manager.conf["output_columns"]:            
            if len(entry[0]):
                splitEntry = entry[0].split('_',1)
                key = splitEntry[0]
                
                if len(splitEntry)==2: subKey = splitEntry[1]
                else: subKey = 'mean'
                
                sampleInfo[entry[1]] = self.new_clickStats[key][subKey]
                sampleInfo["colors"][entry[1]] = self.new_clickStats[key]["colors"][2]
                

        # compile id specific information
        idInfo = OrderedDict()
        idInfo["type"] = self.typeLabel.activeLabel
        for n, entry in enumerate(self.manager.entryDict['id']):
            idInfo[entry] = self.entryHolder['id'][n][0].get()

        if not ID is None:
            sampleInfo["ID"] = ID
            idInfo["type"] = sampleType
            
        self.manager.add(sampleInfo,idInfo)        
        #self.destroy()
            
        
    def change_sampleType(self,event=None, newType=None):                
        if newType is None:
            newType = self.typeLabel.activeLabel
        activeEntries = self.manager.conf["sampleTypes"][newType]

        self.typeLabel.set_activeLabel(newType)

        for i,key in enumerate(["id","sample"]):
            for n,entry in enumerate(self.manager.entryDict[key]):
                if entry in activeEntries[i] or entry in self.manager.generalEntries:
                    self.entryHolder[key][n][0].grid()
                    self.entryHolder[key][n][1].grid()
                else:
                    self.entryHolder[key][n][0].grid_remove()
                    self.entryHolder[key][n][1].grid_remove()

    def export(self):
        self.wm_attributes("-topmost", 0)
        #path='csv/results.csv'
        path = tkAsksaveasfilename(initialdir = "/csv",title = "Select file",filetypes = (("text file","*.csv"),("all files","*.*")))
        if len(path.split('.')) < 2: path = path + '.csv'
        self.manager.export(path)        
        self.wm_attributes("-topmost", 1)
        


