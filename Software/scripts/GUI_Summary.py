import tkinter as tk
from tkinter import filedialog
import time
import datetime
import os
import multiprocessing
#-----------------
import PicarroPeeker
import configLoader
import statLib
import PlotCanvas
import ExtraWidgets
import support
import random

colors = ["#"+''.join([random.choice('0123456789ABCDEF') for j in range(6)]) for i in range(200)]

def invert_color(hexString):
    rgbVals = tuple(255 - int(hexString[i:i+2], 16) for i in (1, 3, 5))
    return"#%02x%02x%02x"%rgbVals
        

def request_picarroDat(backwardsHours, pLogDirs, endTime=None, timeWindow=None):
    if endTime is None:
        endTime = time.time()

    print(pLogDirs)

    for path in [pLogDirs[1]]:
        try:
            pDat = PicarroPeeker.peek(backwardsHours = backwardsHours, logDir = path, timeWindow=timeWindow)
            return pDat
        except:
            print("No log files found in '"+path+"' :(")


class SummarizerFrame(tk.Frame):
    
    def __init__(self, master, options, *args, **kwargs):

        super(SummarizerFrame,self).__init__(master, *args, **kwargs)

        self.conf = configLoader.combine("../config/picarro.cfg", "../config/default/picarro.cfg")

        self.canvasList = []
        self.parListboxLabelX = []
        self.parListboxLabelY = []
        self.latestPicarroPeek = -1
        self.latestPicarroPeekRead = -1
        self.childProcess = None
        self.timeWindow = None
        self.selection = None
        self.summary = None
        
        self.options = options

        x = tk.Frame(self, width=100)
        x.grid(row=0, column=1, rowspan=6, sticky="nsew")

        self.legendCanvas = PlotCanvas.PlotCanvas(x, bg="white", plotRangeX=[0,1], plotRangeY=[0,1],
                                                  height=500, width=100, axes=False, marginX=10, objectClickHandler=self.objectClickHandler)
        self.legendCanvas.grid(row=0, column=0, sticky="nsew", rowspan=2, columnspan=2)

        tk.Label(x, text ='End time (UTC)').grid(row=2,column=0)
        self.endTimeEntry = tk.Entry(x, text="")
        self.endTimeEntry.grid(row=3, column=0)
        self.endTimeEntry.insert(0,support.nowString())

        tk.Label(x, text ='Time window (h)').grid(row=4,column=0)        
        self.timeWindowSelection = tk.Spinbox(x, values=(1,3,6,12,24,48,120,240),width=3)
        self.timeWindowSelection.grid(row=5, column=0, sticky="nsew")
        self.timeWindowSelection.delete(0,"end")
        self.timeWindowSelection.insert(0,24)

        bReload = tk.Button(x, text="Summarize", command = self.triggerPicarroPeek)
        bReload.grid(row=6,column=0)

        bReplot = tk.Button(x, text="Plot again", command = self.plotSummary)
        bReplot.grid(row=7,column=0)

        bRawDat = tk.Button(x, text="Raw data", command = self.plotRawData)
        bRawDat.grid(row=8,column=0)

        bExport = tk.Button(x, text="Export", command = self.export_data)
        bExport.grid(row=9,column=0)

        tk.Label(x, text="IgnoreList").grid(row=10, column=0)
        self.ignoreListEntry = tk.Entry(x)
        self.ignoreListEntry.grid(row=11, column=0)
        

        for i in range(3):

            x = tk.Frame(self)
            x.grid(row=i, column=0, sticky="nsew",pady=0)
            self.rowconfigure(i, weight=1)
            
            self.canvasList.append(PlotCanvas.PlotCanvas(x, bg="white",
                                                         plotRangeX=[0,1],plotRangeY=[0,1],
                                                         height=200, width=400,
                                                         marginX=60, marginY=25,
                                                         objectClickHandler=self.objectClickHandler))
            self.canvasList[i*2].draw_xAxis(timeFormat=None, optimalTicks=5)
            self.canvasList[i*2].grid(row=i*2, column=1)


            option = self.options.index(["d2H","d18O","d2H"][i])
            self.parListboxLabelY.append(ExtraWidgets.ListboxLabel(x, self.options,option, width=5))
            self.parListboxLabelY[i*2].grid(row=i*2,column=0, sticky = 'we')

            option = self.options.index(["d18O","H2O","H2O"][i])
            self.parListboxLabelX.append(ExtraWidgets.ListboxLabel(x, self.options,option))
            self.parListboxLabelX[i*2].grid(row=i*2+1,column=1, sticky = 'we')

            
            self.canvasList.append(PlotCanvas.PlotCanvas(x, bg="white",
                                                         plotRangeX=[0,1],plotRangeY=[0,1],
                                                         height=200, width=600,
                                                         marginX=60, marginY=25,
                                                         selectionHandler = self.change_timeWindow,
                                                         objectClickHandler=self.objectClickHandler))
            self.canvasList[i*2+1].draw_xAxis(timeFormat=None, optimalTicks=8)
            self.canvasList[i*2+1].grid(row=i*2, column=3)

            self.parListboxLabelY.append(ExtraWidgets.ListboxLabel(x, self.options,i+3, width=5))
            self.parListboxLabelY[i*2+1].grid(row=i*2,column=2, sticky = 'we')

            self.parListboxLabelX.append(ExtraWidgets.ListboxLabel(x, self.options,0))
            self.parListboxLabelX[i*2+1].grid(row=i*2+1,column=3, sticky = 'we')

            

            self.update()

    def triggerPicarroPeek(self):

        hours = float(self.timeWindowSelection.get())
        pDat = request_picarroDat(hours, self.conf["rawLogSearchPaths"])
        self.summary = self.summarize(pDat, hours)
        self.plotSummary(self.summary)
        

    def readPicarroPeek(self, timeWindow=None):
        pDat=[]
        with open("../temp/picarro.log", "r") as pf:
            for line in pf:
                firstChar = line[0]
                if firstChar in ["#","t"]:
                    continue
                sl = line.split("\t")

                t = int(sl[0])
                if timeWindow and ((t<timeWindow[0] ) or (t>timeWindow[1])):
                    continue
                
                pDat.append([t, int(sl[1]), float(sl[2]), float(sl[3])])
        self.latestPicarroPeekRead+=1
        return pDat
        

   # def update(self):
    #    self.endTimeEntry.delete(0,"end")
     #   self.endTimeEntry.insert(0,support.nowString())
      #  self.after(500, self.update)

    def plotRawData(self):
        print(self.timeWindow)

        hours = float(self.timeWindowSelection.get())
        pDat = request_picarroDat(hours, self.conf["rawLogSearchPaths"], timeWindow=self.timeWindow)

        print(len(pDat))

        columns = ["time", "H2O", "d18O", "d2H"]

        ###########
        # add code to plot the raw data time series
        ##############

        print(pDat[:10])

    def plotSummary(self, summary=None, selectionInterval=None):

        if summary is None:
            summary = self.summary

        ignoreList = self.ignoreListEntry.get().split(';')
        
        for i in range(len(self.canvasList)):

            labels    = list()            
            xVals     = list()
            yVals     = list()            
            timestamps= list()
            sizeVals  = list()
            lwdVals   = list()            
            selID = None

            ix = self.parListboxLabelX[i].activeIndex
            iy = self.parListboxLabelY[i].activeIndex           

            for val in summary["data"]:
                if val[0] in ["xxx"]+ignoreList: continue

                if selectionInterval:
                    if val[1] < selectionInterval[0] or val[1] > selectionInterval[1]:
                        continue
                
                labels.append(val[0])
                timestamps.append(val[1])
                xVals.append(val[ix+1])
                yVals.append(val[iy+1])

                lwdVals.append(1)

                if self.selection and val[0] == self.selection["ID"]:
                    selID = self.selection["ID"]
                    sizeVals.append(9)                    
                    if self.selection["time"] == "%d"%val[1]:
                        lwdVals[-1] = 3
                else:
                    sizeVals.append(5)

            
            timeFormat = "%H:%M" if summary["columns"][ix+1]=="time" else None
           

            self.canvasList[i].draw_xAxis(plotRangeX=[min(xVals), max(xVals)], timeFormat=timeFormat, precision=0, optimalTicks=5)
            self.canvasList[i].draw_yAxis(plotRangeY=[min(yVals), max(yVals)], optimalTicks=5, precision=0)
            self.canvasList[i].plotLine(-40,-310,40,330, tag="GMWL")
            
            cols=[]
            borderCols = []
            labs=[]
            labCols=[]
            labSize=[]
            uLabels = support.unique(labels)
            for n,l in enumerate(labels):
                cols.append(colors[uLabels.index(l)])
                borderCols.append(invert_color(cols[n]) if lwdVals[n]>1 else "#000000")
                if not l in labs:
                    labs.append(l)
                    labCols.append(cols[-1])
                    labSize.append(8 if l==selID else 5)
            
        
            self.canvasList[i].plotPoints(xVals,yVals,cols, idTag = labels, timestamp=timestamps, size=sizeVals, lwd=lwdVals, borderCol=borderCols)

        self.legendCanvas.plotRangeY = [0,len(labs)]
        self.legendCanvas.plotPoints(x=[0.05 for a in range(len(labs))],
                                     y=list(range(len(labs),-1,-1)),
                                     col=labCols, labels=labs, labelOffsets=[10,0], size=labSize)

    def summarize(self, pDat, timeWindow_in_hours):
        
        valves = {"time":[],"ID":[],"mode":[]}
        valveFile = open(self.conf["valveLogPath"]+"/valves.log","r")                            
        valveDat = valveFile.readlines()
                    
        for splitLine in map(lambda x: x.split('\t'), valveDat[2:]):
            t = datetime.datetime.strptime(splitLine[0], "%Y%m%d%H%M%S")
            t = time.mktime(t.timetuple())
            v = splitLine[1].rstrip()
            m = int(splitLine[2])

            valves["time"].append(t)
            valves["ID"].append(v)
            valves["mode"].append(m)

        res = list()
        for n in range(2,len(valves["time"])-1):
            if valves["mode"][n-1]==0:
                continue

            if valves["ID"][n-2] == valves["ID"][n-1] and valves["mode"][n-2]==0:
                flushTime = valves["time"][n-1] - valves["time"][n-2]
            else:
                flushTime = 0
                
            measureTime = valves["time"][n] - valves["time"][n-1]

            H2O=list()
            d18O=list()
            d2H=list()    
            for p in pDat:
                if p[0] < valves["time"][n]-self.conf["evalSeconds"] or p[0]>valves["time"][n]:
                    continue
                H2O.append(p[1])
                d18O.append(p[2])
                d2H.append(p[3])
                if p[0] > valves["time"][n]:
                    break
            if len(H2O):
                res.append([valves["ID"][n-1], valves["time"][n],
                            flushTime, measureTime,
                            round(statLib.mean(H2O)),                        
                            round(statLib.mean(d18O),2),
                            round(statLib.mean(d2H),1)])

            
        return({"columns":["ID","time","fTime","mTime","H2O","d18O","d2H"], "data":res})


    def export_data(self):
        filepath = filedialog.asksaveasfilename(defaultextension="csv")

        if not len(filepath): return        

        datColumns = [self.summary["columns"].index(x) for x in ["d18O","d2H","H2O"]]
        timeColumn = self.summary["columns"].index('time')
        

        with open(filepath, 'w') as f:
            f.write(';'.join(["Sample","d18O","d2H","H2O","Date","Note","Origin"])+'\n')
            for line in self.summary["data"]:                
                f.write(';'.join([str(line[i]) for i in [0]+datColumns]\
                            +[support.secs2String(line[timeColumn],"%Y-%m-%d"),'','VapAuSa'])\
                        +'\n')
        
        
        

    def plot_selection(self):
    
        if self.currentSelection is None:            
            return

        for plot in self.canvasList:
                    
            plot = self.parCanvas[n]
            lineCol = self.get_colors(status, strongCol=False)["line"]
            plot.delete("selection")
            plot.vertLines(self.currentSelection["interval"],tag = "selection", color=lineCol, width=2)

    def objectClickHandler(self, ID, time):
        self.selection = {"ID":ID, "time":time}
        #print(self.selection)
        self.plotSummary(selectionInterval = self.timeWindow)
            

    def change_timeWindow(self, selectionInterval, button="left"):       

        # on right button click, discard current selection
        if button == "right" or selectionInterval is None:
            self.timeWindow = None

        else:
        
            try:
                selectionInterval.sort()
            except:
                return            
            
            if (selectionInterval[1] - selectionInterval[0]) > 3600:                                
                self.timeWindow = selectionInterval.copy()

        self.plotSummary(selectionInterval = self.timeWindow)        
        

if __name__ == "__main__":
    if 1:
        root = tk.Tk()
        root.title("Summary")
        root.geometry("%dx%d+%d+%d"%(1500,750,1,0))

        sf = SummarizerFrame(root,options=["time","fTime","mTime","H2O","d18O","d2H"])
        sf.pack(fill = tk.BOTH, expand=True)
       # sf.update()
        root.mainloop()

