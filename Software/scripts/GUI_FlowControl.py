import tkinter as tk
from tkinter import font as tkFont
import datetime
import time
import os

import PlotCanvas
import DataBuffer
import configLoader

colors = configLoader.load_confDict("../config/default/colors.cfg",
                                    verbose = __name__=="__main__")
  
class FlowControlFrame(tk.Frame):
    def __init__(self, master, fc, flowConfigFile="../config/flow.cfg", *args, **kwargs):
        super(FlowControlFrame,self).__init__(master,*args, **kwargs)

        self.fc = fc
        self.status = -1
        self.master = master
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_rowconfigure(0, weight=1)

        self.job = None

        self.conf = configLoader.load_confDict(flowConfigFile)        

        if not self.conf["logfile"]:
            logfilePath = None

        #self.fc.apply_calibration(configLoader.load_confDict("../config/flow.cal"))
        
        #----------- preapre the dataBuffer (and logfile) ----------
        rD    = self.conf["relevantDifference"]        
        parList = [DataBuffer.Parameter(name = "flowValueA",   unit = "mL/min", relevantDifference = rD),
                   DataBuffer.Parameter(name = "flowValueB",   unit = "mL/min", relevantDifference = rD),
                   DataBuffer.Parameter(name = "targetValueA", unit = "mL/min", relevantDifference =  0),
                   DataBuffer.Parameter(name = "targetValueB", unit = "mL/min", relevantDifference =  0)]
        
        if "logfile" in self.conf.keys():
            logfile = self.conf["logfile"]
        else:
            None
        
        self.dataBuffer = DataBuffer.Buffer(int(self.conf["bufferSize"]), logfile, parList, flushChunk=20)

        

        #----left frame: controls and labels----------------
        self.font = tkFont.Font(family="Sans", size=11, weight="bold")
        self.leftFrame = tk.Frame(self, width=100)
        self.leftFrame.pack(side=tk.LEFT, fill=tk.Y)

        for n in range(4): self.leftFrame.grid_rowconfigure(n, weight=n>1)

        tk.Label(self.leftFrame, text="flow [mL/min]", font = self.font).grid(row=0,column=1,columnspan=3,sticky="nsew")
        tk.Label(self.leftFrame, text="A", font = self.font, bg = colors["fcA"]).grid(row=1,column=2,columnspan=1,sticky="nsew")
        tk.Label(self.leftFrame, text="B", font = self.font, bg = colors["fcB"]).grid(row=1,column=3,columnspan=1,sticky="nsew")        

        self.flowScaleA = tk.Scale(self.leftFrame, from_=fc.maxFlowA, to=0, orient=tk.VERTICAL, length=50)
        self.flowScaleA.grid(row=2, column=2, rowspan=2, sticky="nsew")
        self.flowScaleA.set(0)
        self.flowScaleA.bind("<ButtonRelease-1>", self.changeFlowRate)

        self.flowScaleB = tk.Scale(self.leftFrame, from_=fc.maxFlowB, to=0, orient=tk.VERTICAL, length=50)
        self.flowScaleB.grid(row=2, column=3, rowspan=2, sticky="nsew")
        self.flowScaleB.set(0)
        self.flowScaleB.bind("<ButtonRelease-1>", self.changeFlowRate)


        #------ right frame: plot canvas ------
        self.plotCanvas = PlotCanvas.PlotCanvas(self, plotRangeX=[0,20], plotRangeY=[0,50], axes=True, bg="white",
                                                marginX=50,marginY=25, height = 300, width  = 400)
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
        self.fc.set_flow(self.flowScaleA.get(), self.flowScaleB.get())
        

    def update(self, selfCalling = True):
        self.status = self.fc.check_status()
    
        newTargets = [self.flowScaleA.get(), self.flowScaleB.get()]
        self.dataBuffer.add(self.fc.get_flow(int(self.conf["decimalPlaces"])) + newTargets, time.time())

        t = self.dataBuffer.get_time(timeOffset = -time.timezone)

        if len(t) > 2:
            flowValueA = self.dataBuffer["flowValueA"]
            flowValueB = self.dataBuffer["flowValueB"]
            flowValueAB = [x + y for x, y in zip(flowValueA, flowValueB)]

            self.plotCanvas.plotRangeY = [0,max(35,max(flowValueAB))]

            if len(flowValueA) > 2:

                self.plotCanvas.draw_xAxis([min(t),max(t)],optimalTicks = 7)                
                self.plotCanvas.plotData(t, flowValueA, tag = "A", color = colors["fcA"],width=2, labelXoffset = 20)
                self.plotCanvas.plotData(t, flowValueB, tag = "B", color = colors["fcB"],width=2, labelXoffset = 50)
                self.plotCanvas.plotData(t, flowValueAB, tag = "AB", width=1, color = "darkgrey", labelXoffset = 80)
    
        if selfCalling:
            self.after(1000, self.update)

    def set(self,flowPattern):
        self.flowScaleA.set(flowPattern.flush.rateA)
        self.flowScaleB.set(flowPattern.flush.rateB)        

    def on_resize(self, event):
        pass
        self.plotCanvas.on_resize(self.winfo_width()-120, self.winfo_height()-15)


if __name__ == "__main__":

    calibration = configLoader.load_confDict("../config/flow.cfg")["calibration"]

    import SerialDevices
    dInfo = SerialDevices.find_device("IsWISaS_Controller", [9600], cachePath = "../temp/serial.cch")   
    try:
        fc = SerialDevices.IsWISaS_Controller(dInfo["port"], dInfo["baudRate"], calibration)
    except:
        fc = SerialDevices.IsWISaS_Controller("foobar", 0)
            
    root = tk.Tk()
    root.title("FlowController")
    root.geometry("%dx%d+%d+%d"%(1280,480,1,0))    
    gui = FlowControlFrame(root, fc, flowConfigFile="../config/flow.cfg", relief=tk.RAISED)
    gui.pack(fill=tk.BOTH, expand=1)
    root.mainloop()

