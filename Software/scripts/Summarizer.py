import tkinter as tk
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

colors=["#f00","#ff0","#0f0","#0ff","#00f","#f0f",                    
        "#700","#770","#070","#077","#007","#707",
        "#b00","#bb0","#0b0","#0bb","#00b","#b0b",
        "#300","#330","#030","#033","#003","#303"]

def request_picarroDat(timeWindow, endTime=None):
    if endTime is None:
        endTime = time.time()
    pLogDir = "../../DataLog_User"
    pDat = PicarroPeeker.peek(logDir = pLogDir, timeWindow_in_hours = timeWindow)

    return pDat
    

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
        
        self.options = options

        x = tk.Frame(self, width=100)
        x.grid(row=0, column=1, rowspan=6, sticky="nsew")

        self.legendCanvas = PlotCanvas.PlotCanvas(x, bg="white", plotRangeX=[0,1], plotRangeY=[0,1],
                                                  height=300, width=100, axes=False, marginX=10)
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
        

        for i in range(3):

            x = tk.Frame(self)
            x.grid(row=i, column=0, sticky="nsew",pady=0)
            self.rowconfigure(i, weight=1)
            
            self.canvasList.append(PlotCanvas.PlotCanvas(x, bg="white",
                                                         plotRangeX=[0,1],plotRangeY=[0,1],
                                                         height=150, width=300,
                                                         marginX=60, marginY=25))
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
                                                         height=150, width=450,
                                                         marginX=60, marginY=25))
            self.canvasList[i*2+1].draw_xAxis(timeFormat=None, optimalTicks=8)
            self.canvasList[i*2+1].grid(row=i*2, column=3)

            self.parListboxLabelY.append(ExtraWidgets.ListboxLabel(x, self.options,i+3, width=5))
            self.parListboxLabelY[i*2+1].grid(row=i*2,column=2, sticky = 'we')

            self.parListboxLabelX.append(ExtraWidgets.ListboxLabel(x, self.options,0))
            self.parListboxLabelX[i*2+1].grid(row=i*2+1,column=3, sticky = 'we')

            self.update()

    def triggerPicarroPeek(self):

        hours = float(self.timeWindowSelection.get())
        pDat = request_picarroDat(hours)
        summary = self.summarize(pDat, hours)
        self.plotSummary(summary)
        

    def readPicarroPeek(self):
        pDat=[]
        with open("../temp/picarro.log", "r") as pf:
            for line in pf:
                firstChar = line[0]
                if firstChar in ["#","t"]:
                    continue
                sl = line.split("\t")
                pDat.append([int(sl[0]), int(sl[1]), float(sl[2]), float(sl[3])])
        self.latestPicarroPeekRead+=1
        return pDat
        

    def update(self):
        self.endTimeEntry.delete(0,"end")
        self.endTimeEntry.insert(0,support.nowString())

        #if not self.childProcess is None:
            

        #if self.latestPicarroPeekRead < self.latestPicarroPeek:

         #   hours = float(self.timeWindowSelection.get())
          #  pDat = self.readPicarroPeek()
           # summary = self.summarize(pDat, hours)
            
            #self.plotSummary(summary)

        self.after(500, self.update)

    def plotSummary(self, summary):
        for i in range(len(self.canvasList)):

            labels = list()
            xVals = list()
            yVals = list()

            ix = self.parListboxLabelX[i].activeIndex
            iy = self.parListboxLabelY[i].activeIndex

            for val in summary["data"]:
                if val[0]=="xxx": continue
                labels.append(val[0])
                xVals.append(val[ix+1])
                yVals.append(val[iy+1])

            if not summary["columns"][ix+1]=="time": timeFormat = None
            else: timeFormat="%H:%M"
            self.canvasList[i].draw_xAxis(plotRangeX=[min(xVals), max(xVals)], timeFormat=timeFormat, precision=0, optimalTicks=5)
            self.canvasList[i].draw_yAxis(plotRangeY=[min(yVals), max(yVals)], optimalTicks=5, precision=0)
            
            cols=[]
            labs=[]
            labCols=[]
            uLabels = support.unique(labels)
            for l in labels:
                cols.append(colors[uLabels.index(l)])
                if not l in labs:
                    labs.append(l)
                    labCols.append(cols[-1])
            
        
            self.canvasList[i].plotPoints(xVals,yVals,cols)

        self.legendCanvas.plotRangeY = [0,len(labs)]
        self.legendCanvas.plotPoints([0.05 for a in range(len(labs))], list(range(len(labs),-1,-1)), labCols, labs, [30,0])

    def summarize(self, pDat, timeWindow_in_hours):
        #pLogDir = "../../DataLog_User"
        #pDat = PicarroPeeker.peek(logDir = pLogDir, timeWindow_in_hours = timeWindow_in_hours)

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

if __name__ == "__main__":

    #pLogDir = "../../DataLog_User"
    #pDat = PicarroPeeker.peek(logDir = pLogDir, timeWindow_in_hours = 48)

    #formatString = "%Y-%m-%d %H:%M"
    #print(support.secs2String(pDat[1][0], formatString),
    #      support.secs2String(pDat[-1][0], formatString))

    if 1:
        root = tk.Tk()
        root.title("Summary")
        root.geometry("%dx%d+%d+%d"%(1000,500,1,0))

        sf = SummarizerFrame(root,options=["time","fTime","mTime","H2O","d18O","d2H"])
        sf.pack(fill = tk.BOTH, expand=True)
       # sf.update()
        root.mainloop()

