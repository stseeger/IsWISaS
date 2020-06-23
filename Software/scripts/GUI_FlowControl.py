import tkinter as tk
from tkinter import font as tkFont
import datetime
import time
import PlotCanvas
import os
import DataBuffer
import configLoader

colors = configLoader.load_confDict("../config/default/colors.cfg")


# format POSIX seconds to a certain time format
def secs2DateString(seconds_POSIX, stringFormat = "%m-%d/%H:%M:%S"):
    return time.strftime(stringFormat,time.gmtime(seconds_POSIX))




class FlowControlFrame(tk.Frame):
    def __init__(self, master, fc, *args, **kwargs):
        super(FlowControlFrame,self).__init__(master, *args, **kwargs)

        self.fc = fc
        self.status = -1
        self.master = master
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_rowconfigure(0, weight=1)

        self.isFlushing = True
        self.isCycling = False
        self.cycleStartTime = time.time()
        self.job = None

        self.conf = configLoader.load_confDict("../config/flow.cfg")
        self.profiles = [self.conf["probeType"][key] for key in self.conf["probeType"].keys()]

        if not self.conf["logfile"]:
            logfilePath = None

        self.fc.apply_calibration(configLoader.load_confDict("../config/flow.cal"))
        
        #----------- preapre the dataBuffer (and logfile) ----------
        parList = [DataBuffer.Parameter(name = "flowValueA", unit = "mL/min", relevantDifference = self.conf["logPrecision"]),
                   DataBuffer.Parameter(name = "flowValueB", unit = "mL/min", relevantDifference = self.conf["logPrecision"]),
                   DataBuffer.Parameter(name = "targetValueA", unit = "mL/min", relevantDifference = 0),
                   DataBuffer.Parameter(name = "targetValueB", unit = "mL/min", relevantDifference = 0)]
        
        if "logfile" in self.conf.keys():
            logfile = self.conf["logfile"]
        else:
            None
        
        self.dataBuffer = DataBuffer.Buffer(600, logfile, parList, flushChunk=20)

        

        #----left frame: controls and labels----------------
        self.font = tkFont.Font(family="Sans", size=11, weight="bold")
        self.leftFrame = tk.Frame(self, width=100)
        self.leftFrame.pack(side=tk.LEFT, fill=tk.Y)

        for n in range(4): self.leftFrame.grid_rowconfigure(n, weight=n>1)

        tk.Label(self.leftFrame, text="flow [mL/min]", font = self.font).grid(row=0,column=1,columnspan=3,sticky="nsew")
        tk.Label(self.leftFrame, text="A", font = self.font, bg = colors["fcA"]).grid(row=1,column=2,columnspan=1,sticky="nsew")
        tk.Label(self.leftFrame, text="B", font = self.font, bg = colors["fcB"]).grid(row=1,column=3,columnspan=1,sticky="nsew")        

        self.button_flush = tk.Button(self.leftFrame, command=self.toggle_mode, text="flush" , font=self.font, wraplength = 1, relief = tk.SUNKEN, bg=colors["active"])
        self.button_flush.grid(row=2, column=1,sticky="nsew")
        self.button_measure = tk.Button(self.leftFrame, command=self.toggle_mode, text="measure" , font=self.font, wraplength = 1, relief = tk.RAISED)
        self.button_measure.grid(row=3, column=1,sticky="nsew")
        colors["neutralButton"] = self.button_measure.cget("bg")

        self.flushScaleA = tk.Scale(self.leftFrame, from_=fc.maxFlowA, to=0, orient=tk.VERTICAL, length=50, bg=colors["flush"])
        self.flushScaleA.grid(row=2, column=2, sticky="nsew")
        self.flushScaleA.set(self.profiles[0]["fRateA"])
        self.flushScaleA.bind("<ButtonRelease-1>", self.changeFlowRate)

        self.measureScaleA = tk.Scale(self.leftFrame, from_=fc.maxFlowA, to=0, orient=tk.VERTICAL, length=50, bg=colors["measure"])
        self.measureScaleA.grid(row=3, column=2, sticky="nsew")
        self.measureScaleA.set(self.profiles[0]["mRateA"])
        self.measureScaleA.bind("<ButtonRelease-1>", self.changeFlowRate)

        self.flushScaleB = tk.Scale(self.leftFrame, from_=fc.maxFlowB, to=0, orient=tk.VERTICAL, length=50, bg=colors["flush"])
        self.flushScaleB.grid(row=2, column=3, sticky="nsew")
        self.flushScaleB.set(self.profiles[0]["fRateB"])
        self.flushScaleB.bind("<ButtonRelease-1>", self.changeFlowRate)

        self.measureScaleB = tk.Scale(self.leftFrame, from_=fc.maxFlowB, to=0, orient=tk.VERTICAL, length=50, bg=colors["measure"])
        self.measureScaleB.grid(row=3, column=3, sticky="nsew")
        self.measureScaleB.set(self.profiles[0]["mRateB"])
        self.measureScaleB.bind("<ButtonRelease-1>", self.changeFlowRate)


        #------ right frame: plot canvas ------
        self.plotCanvas = PlotCanvas.PlotCanvas(self, plotRangeX=[0,20],plotRangeY=[0,50],
                                                marginX=50,marginY=25, height=400, width=400,
                                                axes=True, bg="white")
        self.plotCanvas.create_text(400, 50, text="waiting for connection...", font = tkFont.Font(size=20), tags = "initial")

        self.plotCanvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=1)
        
        #-------------------

        self.bind("<Configure>", self.on_resize)


        self.changeFlowRate()
                
        self.update()
        self.after(5000,self.after_startup)

    def after_startup(self):
        self.plotCanvas.delete("initial")
        self.plotCanvas.create_text(400, 50, text="no connection to flow controller...", font = tkFont.Font(size=20), tags = "error")
        self.update(False)
        self.on_resize(None)
        

    def changeFlowRate(self, event=None):
        if self.isFlushing:
            self.fc.set(self.flushScaleA.get(), self.flushScaleB.get())
        else:
            self.fc.set(self.measureScaleA.get(), self.measureScaleB.get())

    def toggle_mode(self, isFlushing = None):
        defaultbg = colors["neutralButton"]
        activebg = colors["active"]

        if isFlushing is None:
            self.isFlushing = not self.isFlushing
        else:
            self.isFlushing = isFlushing

        self.button_flush.config(relief = [tk.RAISED, tk.SUNKEN][1*self.isFlushing], bg = [defaultbg, activebg][1*self.isFlushing])
        self.button_measure.config(relief = [tk.SUNKEN, tk.RAISED][1*self.isFlushing], bg = [activebg, defaultbg][1*self.isFlushing])
        self.changeFlowRate()
        
    def set_flushMode(self, flushMode):
        self.toggle_mode(flushMode)
        

    def update(self, selfCalling = True):
        self.status = self.fc.check_status()
        
        if self.isFlushing:
            newTargets = [self.flushScaleA.get(), self.flushScaleB.get()]
        else:
            newTargets = [self.measureScaleA.get(), self.measureScaleB.get()]          
            
        self.dataBuffer.add(self.fc.get(), self.fc.lastGetTime)

        t = self.dataBuffer.get_time()

        if len(t) > 2:
            flowValueA = self.dataBuffer["flowValueA"]
            flowValueB = self.dataBuffer["flowValueB"]
            flowValueAB = [x + y for x, y in zip(flowValueA, flowValueB)]

            self.plotCanvas.plotRangeY = [0,max(flowValueAB)]

            if len(flowValueA) > 2:

                self.plotCanvas.draw_xAxis([min(t),max(t)],optimalTicks = 7)                
                self.plotCanvas.plotData(t, flowValueA, tag = "A", color = colors["fcA"],width=2, labelXoffset = 20)
                self.plotCanvas.plotData(t, flowValueB, tag = "B", color = colors["fcB"],width=2, labelXoffset = 50)
                self.plotCanvas.plotData(t, flowValueAB, tag = "AB", width=1, color = "darkgrey", labelXoffset = 80)
    
        if selfCalling:
            self.after(1000, self.update)

    def set(self,flowPattern):
        self.flushScaleA.set(flowPattern.flush.rateA)
        self.flushScaleB.set(flowPattern.flush.rateB)
        self.measureScaleA.set(flowPattern.measure.rateA)
        self.measureScaleB.set(flowPattern.measure.rateB)

    def on_resize(self, event):
        self.plotCanvas.on_resize(self.master.winfo_width()-160, self.master.winfo_height())
          

if __name__ == "__main__":
    import SerialDevices
    deviceDict, portDict = SerialDevices.scan_serialPorts(9600)
    if "FlowController" in deviceDict.keys():        
        fc = SerialDevices.FlowController(deviceDict["FlowController"].port, deviceDict["FlowController"].baudRate)
    else:
        try:
            fc = SerialDevices.SierraFlowController(COM_Port_FlowController, 9600)
            print.fc.status
        except:
            fc = SerialDevices.FlowController("foobar", 0)
    root = tk.Tk()
    root.title("FlowController")
    root.geometry("%dx%d+%d+%d"%(1280,480,1,0))
    gui = FlowControlFrame(root, fc, relief=tk.RAISED)
    gui.pack(fill=tk.BOTH, expand=1)
    root.mainloop()

