import tkinter as tk
import collections
import math
#---------------------
import LogFileReader
import DataBuffer
import PlotCanvas
import ExtraWidgets
import statLib

COLOR_PLOTLINE = "black"

#=====================

renameDict = {"current":"  ", "mean":u'\u03bc:', "sd":u'\u03c3:', "trend":"IT:"}

colDict_lines ={"neutral": "#888",
                "pass": "#00f",
                "fail": "#f00"}

colDict_labels = {"neutral": "#eee",
                  "pass": "#ccf",
                  "fail": "#fcc"}

def summary(values):
    result = collections.OrderedDict()
    result["current"] = values[-1]
    result["mean"] = statLib.mean(values)
    result["sd"] = statLib.sd(values)
    result["trend"] = statLib.trendIndex(values)
    result["_min"] = min(values)
    result["_max"] = max(values)   
    result["_precision"] = max(0,2-round(math.log(max(values)-min(values),10)))
    return(result)


class LogFilePlotter(tk.Frame):
    def __init__(self, master, reader, parList, critParTable=None, *args, **kwargs):

        super(LogFilePlotter,self).__init__(master, *args, **kwargs)
        
        self.reader = reader        
        self.parList = parList
        self.master = master

        self.parCanvas = []
        self.parListboxLabel = []
        self.statLabels = []
        self.recentStats = None
        self.critParTable = critParTable

        self.currentSelection = None

        #----- out source to cfg file...
        self.plotMinutes = 1200
        self.evalSeconds = 120
        #------------------------------

        self.master.grid_columnconfigure(1, weight=1)
        self.master.grid_rowconfigure(0, weight=1, pad=0)        

        self.parentFrame = tk.Frame(self)
        self.parentFrame.grid(sticky='nsew')
        self.parentFrame.grid_columnconfigure(2, weight=1)        

        self.canvasHolders = {}

        dummySummary = summary([0,1,2,3,4,5])

        for i, parName in enumerate(self.parList):
            x = tk.Frame(self.parentFrame)
            self.parCanvas.append(PlotCanvas.PlotCanvas(x, plotRangeX=[0,20],plotRangeY=[0,20],
                                                           marginX=60,marginY=17,
                                                           axes=True,bg="white",
                                                           selectionHandler = self.change_selection,
                                                           height=117, width=600))            

            self.parCanvas[i].grid(row=0,column=0, rowspan=len(dummySummary.keys())+2, sticky='nsew')
            x.grid(row=i,column=0, columnspan=3, sticky='nsew',pady=0)

            self.parListboxLabel.append(ExtraWidgets.ListboxLabel(x, self.reader.dataBuffer.keys(),i))
            self.parListboxLabel[i].grid(row=0,column=1, sticky = 'we')

            tk.Label(x, text='').grid(row=4,column=1) # dummy label for spacing
 
            labelDict = {}
            for n,key in enumerate(dummySummary.keys()):
                if key.startswith("_"): continue
                labelDict[key] = tk.Label(x,  text=key)
                labelDict[key].grid(row=n+1, column=1)

            self.statLabels.append(labelDict)

            self.canvasHolders[parName] = x

        self.update()

    def check_status(self, parName, statistics):
        if not parName in self.critParTable.keys():
            return(None)
        critPars = self.critParTable[parName]
        status = {}
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
            
        

    def update(self):

        self.reader.update()

        
        t = self.reader.dataBuffer.get_time()
        stopIndex = len(t)
        for startIndex in range(len(t)):
            if t[startIndex] > (t[-1] - self.plotMinutes*60):
                break
        startIndex = max([startIndex-1,0])
        t = t[startIndex:stopIndex]

        for evalStartIndex in range(len(t)):
            if t[evalStartIndex] > (t[-1]-self.evalSeconds):
                break
        evalStartIndex = max([evalStartIndex-1,0])

        # reset recent statistics
        self.recentStats = {}

        allPass = True

        for n,parName in enumerate(self.parList):
            
            # get values and compute statistics for parameter
            values = self.reader.dataBuffer[parName][startIndex:]
            evalValues = values[evalStartIndex:]
            valStats = summary(evalValues)
            self.recentStats[parName] = valStats
            status = self.check_status(parName, valStats)

            allPass = allPass and status["all"]

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
            plot = self.parCanvas[n]
            plot.delete(["values","eval"])
            plot.draw_xAxis([t[0],t[-1]],optimalTicks = 10)
            plot.draw_yAxis([min(values),max(values)], 2, optimalTicks = 5)
            plot.plotData(t, values, tag="values", color = colDict_lines["neutral"])
            plot.plotData(t[evalStartIndex:], values[evalStartIndex:], "eval", cols["line"], 3)
            self.plot_selection()

        self.after(500, self.update)
                        

    def plot_selection(self):
    
        if self.currentSelection is None:            
            return

        for n,parName in enumerate(self.parList):
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
            for n,parName in enumerate(self.parList):
                self.parCanvas[n].delete("selection")    
            return
        
        selectionInterval.sort()
        self.currentSelection = {"interval": selectionInterval, "parDict": {}}

        # treat cases where a single click instead of a real selection took place
        if selectionInterval[0] == selectionInterval[1]:
            selectionInterval[0] = max(0, selectionInterval[0]-self.evalSeconds)            

        # get startIndex and length of the selected period
        t = self.reader.dataBuffer.get_time()
        for startIndex, startT in enumerate(t):
            if startT >= selectionInterval[0]:
                break
        for selLength, endT in enumerate(t[startIndex:]):
            if endT >= selectionInterval[1]:
                break

        for parName in self.reader.dataBuffer.keys():

            # get values of selection, compute summary and check status
            values = self.reader.dataBuffer[parName][startIndex:(startIndex+selLength+1)]          
            stats = summary(values)           

            stats["trendChar"] = [u'\u2197', u'\u2197'][int(stats["trend"]>0)]
            stats["trend"] = abs(stats["trend"])

            stats["duration"] = selectionInterval[1] - selectionInterval[0]
            stats["center"]   = selectionInterval[0] + stats["duration"]/2

            self.currentSelection["parDict"][parName] = stats        

        self.plot_selection()
                    

    def on_resize(self,event):
        width = self.master.winfo_width()
        height = self.master.winfo_height()
        for i in range(len(self.parList)):
            self.parCanvas[i].on_resize(width-100,(height-10)/len(self.parList)-6)           


if __name__ == "__main__":

    root = tk.Tk()
    root.title("Picarro")
    root.geometry("%dx%d+%d+%d"%(1280,500,1,0))

    import configLoader
    picarro = configLoader.load_confDict("../config/picarro.cfg")

    configFile = "../config/logDescriptors/picarroLxxxx-i.lgd"
    logDir = "../../../picarroLogs/fake"

    lfr = LogFileReader.Reader(configFile, logDir)
    lfr.fill_dataBuffer()    
    
    lfp = LogFilePlotter(root, lfr, ["H2O","deltaD", "delta18O"], picarro["critPars"])
    lfp.pack(fill = tk.BOTH, expand=True)
    lfp.bind("<Configure>", lfp.on_resize)

    
