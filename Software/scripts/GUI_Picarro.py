import tkinter as tk
import collections
import math
import os
import time
#---------------------
import LogFileReader
import DataBuffer
import PlotCanvas
import ExtraWidgets
import statLib
import configLoader
import SocketPickle
import support

COLOR_PLOTLINE = "black"

#=====================

renameDict = {"current":"  ", "mean":u'\u03bc:', "sd":u'\u03c3:', "trend":u'I\u209c:'}

colDict_lines ={"neutral": "#888",
                "pass": "#00f",
                "fail": "#f00"}

colDict_labels = {"neutral": "#eee",
                  "pass": "#ccf",
                  "fail": "#fcc"}


def startTimeFromFilepathFun(filepath):    
    s = filepath.split('/')[-1].split('-')
    d = s[1]
    t = s[2].replace("Z","")
    if len(t)==4:
        t = t+'00'
    return support.string2Secs(d+t, formatString="%Y%m%d%H%M%S")
 
#----------------------------

def summary(values):    
    result = collections.OrderedDict()
    result["current"] = values[-1]
    result["mean"] = statLib.mean(values)
    result["sd"] = statLib.sd(values)
    result["trend"] = statLib.trendIndex(values)
    result["_min"] = min(values)
    result["_max"] = max(values)   

    result["_precision"] = 1
    #if not all(value == 0 for value in values):
    #    try:
    #        result["_precision"] = 
    #    except: pass
    return(result)


class PicarroFrame(tk.Frame):
    def __init__(self, master, conf, *args, **kwargs):

        super(PicarroFrame,self).__init__(master, *args, **kwargs)
        
        self.master = master

        if type(conf) is dict:
            self.conf=conf
        else:
            self.conf = configLoader.load_confDict(conf)

        conf = self.conf

        # try to locate the picarro log dir
        if type(conf["rawLogSearchPaths"]) is list:
            for entry in conf["rawLogSearchPaths"]:
                if os.path.exists(entry):
                    logDir = entry
                    break
        else:
            logDir = conf["rawLogSearchPaths"]
        print(logDir)
        print('XXXXXXXXXXXXXXXXXXXXXXXXXXXXXx')
        # initialize the picarro log file reader
        self.reader = LogFileReader.Reader(conf["logDescriptor"], logDir,
                                           bufferSize = int(conf["bufferSize"]),
                                           startTimeFromFilepathFun = startTimeFromFilepathFun)

        self.parCanvas = []
        self.parListboxLabel = []
        self.statLabels = []
        self.recentStats = None
        self.conf = conf

        self.current = collections.OrderedDict()
        for p in self.conf["plotPars"]:
            self.current[p] = 0

        self.currentSelection = None
        self.latestInfo = None

        self.currentRecord = 0

        #------------------------------       

        self.canvasHolders = collections.OrderedDict()

        dummySummary = summary([0,1,2,3,4,5])

        for i, parName in enumerate(self.conf["plotPars"]):

            x = tk.Frame(self)
            x.grid(row=i,column=0, sticky='nsew',pady=0)
            self.rowconfigure(i, weight=1)

            x.columnconfigure(0,weight=1)
            x.columnconfigure(1,weight=1)

            self.parCanvas.append(PlotCanvas.PlotCanvas(x, plotRangeX=[0,20],plotRangeY=[0,20],
                                                           marginX=60,marginY=17,
                                                           axes=True,bg="white",
                                                           selectionHandler = self.change_selection,
                                                           height=117, width=600))            

            self.parCanvas[i].grid(row=0,column=0, rowspan=len(dummySummary.keys())+2, sticky='nsew')
            #x.rowconfigure(0, weight=1)
                        
            self.parListboxLabel.append(ExtraWidgets.ListboxLabel(x, self.reader.dataBuffer.keys(),i))
            self.parListboxLabel[i].grid(row=1,column=1, sticky = 'we')            

            tk.Label(x, text='').grid(row=4,column=1) # dummy label for spacing
 
            labelDict = collections.OrderedDict()
            for n,key in enumerate(dummySummary.keys()):
                if key.startswith("_"): continue
                labelDict[key] = tk.Label(x,  text=key)
                labelDict[key].grid(row=n+2, column=1, sticky="nsew")
                x.rowconfigure(2*n, weight=1)
                x.rowconfigure(2*n+1, weight=1)

            self.statLabels.append(labelDict)

            self.canvasHolders[parName] = x

        self.bind("<Configure>", self.on_resize)        

        #----------        

        self._buttonImages = collections.OrderedDict()
        for name in ["start_24", "pause_24", "refresh_16"]:
            try:
                image = tk.PhotoImage(file="../images/"+name+".gif")
            except:
                image = None
            self._buttonImages[name] = image
        
        refreshButton = tk.Button(self.canvasHolders[parName], text="Reload", command = self.reload_configuration, image=self._buttonImages["refresh_16"])
        refreshButton.place(rely=1.0, relx=1.0, x=0, y=0, anchor=tk.SE)
        ExtraWidgets.ToolTip(refreshButton, text="Reload evaluation specs\n(from piccaro.cfg)")

        self.pauseButton = tk.Button(self.canvasHolders[parName], text="Reload", command = self.toggle_plotState, image=self._buttonImages["pause_24"])
        self.pauseButton.place(rely=1., relx=1.0, x=-40, y=0, anchor=tk.SE)
        ExtraWidgets.ToolTip(self.pauseButton, text="Pause/Resume plotting")
        self.do_plots = True

        #----------
        self.master.bind("<KeyPress>", self.keydown)        
        self.maxZoomOutMinutes = self.conf["plotMinutes"]
        self.lastPlotRange = [time.time()-60, time.time()]
        #---------

        self.update()
        

    def keydown(self,event):

        # handle up/down keys to decrease/increase the zoom level
        if event.keysym == "Up":
            self.conf["plotMinutes"] = min(self.maxZoomOutMinutes, self.conf["plotMinutes"]+10)

        if event.keysym == "Down":
            self.conf["plotMinutes"] = max(10,self.conf["plotMinutes"]-10)


        # handle +/- keys to increase/decerase the detail level during plotting
        plotLumpSizes = [1,5,10,50,100]
        if event.char == "-":            
            for s in plotLumpSizes:
                if s > self.conf["plotLumpSize"]: break
            self.conf["plotLumpSize"] = s

        if event.char == "+":            
            for s in plotLumpSizes[::-1]:
                if s < self.conf["plotLumpSize"]: break
            self.conf["plotLumpSize"] = s
                


    def toggle_plotState(self, do_plots=None):
        if do_plots is None:
            self.do_plots = not self.do_plots
            
        self.pauseButton.config(image=self._buttonImages[["pause_24","start_24"][not self.do_plots]])
        

    def reload_configuration(self):
        freshConf = configLoader.load_confDict(self.conf["confFile"])
        self.conf = freshConf.copy()       

    def check_status(self, parName, statistics):
        if not parName in self.conf["critPars"].keys():
            return(None)
        critPars = self.conf["critPars"][parName]
        status = collections.OrderedDict()
        status["all"] = True
        for key in critPars:
            status[key] = abs(statistics[key]) <= abs(critPars[key])
            status["all"] = status["all"] and status[key]

        return(status)

    def get_colors(self, status, strongCol=True):
        if status is None:
            cols = {"line": colDict_lines["neutral"]}
        elif strongCol:
            cols = {"line": colDict_lines[["fail","pass"][int(status["all"])]]}
        else:
            cols = {"line": colDict_labels[["fail","pass"][int(status["all"])]]}
                    
        for key in self.statLabels[0].keys():
            if status is None or key not in status.keys():
                cols[key] = colDict_labels["neutral"]
            else:
                cols[key] = colDict_labels[["fail","pass"][int(status[key])]]

        return(cols)

    def broadcast(self, message):
        SocketPickle.broadcast(self.conf["socket_Host"],
                               self.conf["socket_Port"],
                               message)

    def update(self):

        self.reader.update()        
        
        t = self.reader.dataBuffer.get_time(timeOffset = self.conf["picarroTimeOffset"]*3600-time.timezone)

        if not len(t):
            return

        self.maxZoomOutMinutes = (t[-1]-t[0])/60

        stopIndex = len(t)-1     
        
        for startIndex in range(len(t)):
            if t[startIndex] > (t[stopIndex] - self.conf["plotMinutes"]*60):
                break
        startIndex = max([startIndex-1,0])

        t = t[startIndex:stopIndex]

        self.lastPlotRange = [t[0], t[1]]

        for evalStartIndex in range(len(t)):
            if t[evalStartIndex] > (t[-1]-self.conf["evalSeconds"]):
                break
        evalStartIndex = max([evalStartIndex-1,0])        
        self.recentStats = collections.OrderedDict()
        allPass = True

        
        for n,parName in enumerate(self.conf["plotPars"]):
            
            # get values and compute statistics for parameter
            values = self.reader.dataBuffer[parName][startIndex:]

            
            evalValues = values[evalStartIndex:]
            valStats = summary(evalValues)
            self.recentStats[parName] = valStats
            status = self.check_status(parName, valStats)

            self.current[parName] = values[-1]            
            allPass = allPass and status is not None and status["all"]            

            # in case the plot canvas was manually set to another parameter,
            # repeat value retrieval and computation of statistics
            if parName != self.parListboxLabel[n].activeLabel:
                parName = self.parListboxLabel[n].activeLabel
                values = self.reader.dataBuffer[parName][startIndex:]
                evalValues = values[evalStartIndex:]
                valStats = summary(evalValues)                

            status = self.check_status(parName, valStats)
            cols = self.get_colors(status)            
            
            # update statistics labels of the current subplot
            for key in valStats.keys():
                if key.startswith("_"): continue
                self.statLabels[n][key].config(text = "%s %6.*f %s"%(renameDict[key], valStats["_precision"],valStats[key], self.reader.dataBuffer.get_unit(parName)),
                                               bg = cols[key])            

            # update value plots of the current subplot
            if self.do_plots:                
                plot = self.parCanvas[n]
                plot.delete(["values","eval"])
                plot.draw_xAxis([t[0],t[-1]],optimalTicks = 10)
                plot.draw_yAxis([min(values),max(values)], 2, optimalTicks = 5)
                plot.plotData(t, values, tag="values", color = colDict_lines["neutral"], plotLumpSize=self.conf["plotLumpSize"])
                plot.plotData(t[evalStartIndex:], values[evalStartIndex:], "eval", cols["line"], 3)
                self.plot_selection()

        self.is_stable = allPass


        self.latestInfo = {"H2O": self.current["H2O"],
                           "stable": allPass}

        self.broadcast(self.latestInfo)

        self.after(500, self.update)
                        

    def plot_selection(self):
    
        if self.currentSelection is None:            
            return

        for n,parName in enumerate(self.conf["plotPars"]):
            parName = self.parListboxLabel[n].activeLabel

            stats = self.currentSelection["parDict"][parName]            
            
            status = self.check_status(parName, stats)            
            plot = self.parCanvas[n]            
            
            x = stats["center"]
            y0 = [0.25,0.75][self.currentSelection["parDict"][parName]["mean"] < (plot.plotRangeY[0] + plot.plotRangeY[1])/2]
            y = [y0+y for y in [0.15, 0.05, -0.05, -0.15]]

            lineCol = self.get_colors(status, strongCol=False)["line"]

            plot.delete("selection")
            plot.vertLines(self.currentSelection["interval"],                                          tag = "selection", color=lineCol, width=2)
            plot.relativeLabel(x, y[0], '%s: %.*f'%(u'\u03bc', stats["_precision"], stats["mean"]),    tag = ("selection", "mean"),    color="#000")
            plot.relativeLabel(x, y[1], '%s: %.*f'%(u'\u03c3', stats["_precision"], stats["sd"]),      tag = ("selection", "sd"),      color="#000")
            plot.relativeLabel(x, y[2], '%s: %.*f'%(stats["trendChar"], stats["_precision"], stats["trend"]),   tag = ("selection", "trend"),   color="#000")
            plot.relativeLabel(x, y[3], '%s: %.0fs'%('t',                           stats["duration"]),tag = ("selection", "duration"),color="#000")
        

    def change_selection(self, selectionInterval, button="left"):

        # on right button click, discard current selection
        if button == "right" or selectionInterval is None:
            self.currentSelection = None
            for n,parName in enumerate(self.conf["plotPars"]):
                self.parCanvas[n].delete("selection")    
            return
        
        try:
            selectionInterval.sort()
        except:
            return
        self.currentSelection = {"interval": selectionInterval, "parDict": collections.OrderedDict()}

        # treat cases where a single click instead of a real selection took place
        if selectionInterval[0] == selectionInterval[1]:
            selectionInterval[0] = max(0, selectionInterval[0]-self.conf["evalSeconds"])            

        # get startIndex and length of the selected period
        t = self.reader.dataBuffer.get_time(timeOffset = self.conf["picarroTimeOffset"]*3600-time.timezone)
        for startIndex, startT in enumerate(t):
            if startT >= selectionInterval[0]:
                break
        for selLength, endT in enumerate(t[startIndex:]):
            if endT >= selectionInterval[1]:
                break

        for parName in self.reader.dataBuffer.keys():

            # get values of selection, compute summary and check status
            endIndex = max(startIndex+2,(startIndex+selLength+1))
            values = self.reader.dataBuffer[parName][startIndex:endIndex]          
            stats = summary(values)           

            stats["trendChar"] = [u'\u2197', u'\u2197'][int(stats["trend"]>0)]
            stats["trend"] = abs(stats["trend"])

            stats["duration"] = selectionInterval[1] - selectionInterval[0]
            stats["center"]   = selectionInterval[0] + stats["duration"]/2

            self.currentSelection["parDict"][parName] = stats        

        self.plot_selection()
                    

    def on_resize(self,event):
        #pass
        width = self.winfo_width() -110
        height = self.winfo_height() / len(self.conf["plotPars"])-13
        for i in range(len(self.conf["plotPars"])):
            self.parCanvas[i].on_resize(width,height)

#------------------------------------------

class ValvePicarroFrame(PicarroFrame):
        def __init__(self, master, conf, *args, **kwargs):

            if not type(conf) is dict:
                conf = configLoader.load_confDict(conf)            

            self.valveReader = LogFileReader.Reader(conf["valveLogDescriptor"], conf["valveLogPath"])
            super(ValvePicarroFrame,self).__init__(master, conf, *args, **kwargs)

        def update(self):
            super(ValvePicarroFrame,self).update()
            self.valveReader.update()

            t = self.valveReader.dataBuffer.get_time(timeOffset = self.conf["valveTimeOffset"]*3600-time.timezone)
            v = self.valveReader.dataBuffer["ID"]            

            if not len(t):
                return

            changeTimes = []
            startTimes = []
            startLabels = []

            for i in range(1,len(t)):

                if t[i] < self.lastPlotRange[0]:
                    continue
                
                if v[i] == v[i-1]:
                    changeTimes.append(t[i])
                else:
                    startTimes.append(t[i])
                    startLabels.append(v[i])            

            for n,parName in enumerate(self.conf["plotPars"]):                
                plot = self.parCanvas[n]
                plot.vertLines(startTimes, labels = startLabels, tag = "valveStarts", color="gray60", width=1)
                plot.vertLines(changeTimes, tag = "valveChanges", color="gray90", width=1)


if __name__ == "__main__":

    root = tk.Tk()
    root.title("Picarro")
    root.geometry("%dx%d+%d+%d"%(1000,500,1,0)) 
    
    pf = ValvePicarroFrame(root, "../config/picarro.cfg")
    pf.pack(fill = tk.BOTH, expand=True)

    root.mainloop()

    

    
