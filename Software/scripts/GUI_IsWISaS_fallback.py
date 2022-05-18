import configLoader
import SocketPickle
import SerialDevices
import LogFileReader
import ExtraWidgets
import const

import Sequencer
import GUI_ValveControl
import GUI_FlowControl
import GUI_Picarro

import os
import time
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkFont


def secs2DateString(seconds_POSIX, stringFormat = "%m-%d/%H:%M:%S"):
    return time.strftime(stringFormat,time.gmtime(seconds_POSIX))

class MetaController():
    def __init__(self, sequence, flow, picarro=None):

        self.sequence = sequence
        self.flow = flow
        self.picarro = picarro

        sequence.metaController = self
        flow.metaController = self
        if not picarro is None:
            picarro.metaController = self


class ValveControlFrame(GUI_ValveControl.ValveControlFrame):

    def __init__(self, master, probeSequencer, *args, **kwargs):
        super(ValveControlFrame,self).__init__(master, probeSequencer, *args, **kwargs)

        self.conf = self.sequ.conf
        self.picarroInfo = None
        
        ExtraWidgets.ToolTip(self.extraLabel, u"Current H\u2082O values from the Picarro\n"+\
                                            u"Left click: enable/disable H\u2082O adapted valve switching") 
        #self.check_Picarro()

    def extraLabel_click(self, event=None):
        self.conf["autoSwitchEnable"] = not (self.conf["autoSwitchEnable"] > 0)

    def update(self):
        try:
            self.check_Picarro()
        except:
            pass
        super(ValveControlFrame,self).update()       

    def check_Picarro(self):        
        try:
            self.sequ.picarroInfo = self.sequ.metaController.picarro.latestInfo
        except:
            self.sequ.picarroInfo = SocketPickle.receive(self.conf["socket_Host"], self.conf["socket_Port"])
    
    
class FlowControlFrame(GUI_FlowControl.FlowControlFrame):

    def __init__(self, master, fc, flowConfigFile, valveReader, *args, **kwargs):
        self.valveReader = valveReader
        self.currentProbe = None
        self.metaController = None
        
        super(FlowControlFrame,self).__init__(master, fc, flowConfigFile, *args, **kwargs)

    def synchronizeFlow(self):
        #try:
        flowPattern = self.metaController.sequence.get_activeProbeProfile()
        probe = self.metaController.sequence.activeProbe
        #except:
        #    return

        self.flowScaleA.set(flowPattern[probe.mode]["flowA"])
        self.flowScaleB.set(flowPattern[probe.mode]["flowB"])
        self.changeFlowRate()


    def update(self, selfCalling=True):
        super(FlowControlFrame,self).update(selfCalling)
        #self.valveReader.update()

        if self.metaController is None:
            print("!!!")
            return

        #----
        flowPattern = self.metaController.sequence.get_activeProbeProfile()
        
        if self.currentProbe is None:
            self.currentProbe = self.metaController.sequence.activeProbe
            self.currentMode = self.currentProbe.mode
            self.synchronizeFlow()

        if self.currentProbe != self.metaController.sequence.activeProbe or\
           self.currentMode != self.currentProbe.mode:

            self.currentProbe = self.metaController.sequence.activeProbe
            self.currentMode = self.currentProbe.mode

            self.synchronizeFlow()
        #----
        
        try:
            timeOffset = self.metaController.picarro.conf["valveTimeOffset"]*3600-time.timezone
        except:
            timeOffset = -time.timezone
        
        try:
            t = self.valveReader.dataBuffer.get_time(timeOffset = timeOffset)
            v = self.valveReader.dataBuffer["ID"]
        except:
            t=[]

        if not len(t):
            return

        startTimes = [t[0]]
        startLabels = [v[0]]
        changeTimes = []

        for i in range(1,len(t)):
            if v[i] == v[i-1]:
                changeTimes.append(t[i])
            else:
                startTimes.append(t[i])
                startLabels.append(v[i])

        plot = self.plotCanvas
        plot.vertLines(startTimes, labels = startLabels, tag = "valveStarts", color="gray60", width=1)
        plot.vertLines(changeTimes, tag = "valveChanges", color="gray90", width=1)

        

class PicarroFrame(GUI_Picarro.ValvePicarroFrame):

    def broadcast(self, message):
        super(PicarroFrame, self).broadcast(message)

if __name__ == "__main__":
        
    # load the flow calibration before initializing the hardware
    flowCalibration = configLoader.load_confDict("../config/flow.cfg")["calibration"]
    colors = configLoader.load_confDict("../config/default/colors.cfg")


    print('################################')
    print('Connecting to IsWISaS_Controller...')

    # scan all ports to find the one, where the "IsWISaS_Controller" is connected
    #deviceDict, portDict = SerialDevices.scan_serialPorts(9600, "../temp/serial.cch")

    dInfo = SerialDevices.find_device("IsWISaS_Controller", [9600], cachePath = "../temp/serial.cch")

    try:
        d = SerialDevices.IsWISaS_Controller(dInfo["port"], dInfo["baudRate"], flowCalibration)
        if d.status == 0:
            print("Device not found at the cached serial port...")
            deviceDict, portDict = SerialDevices.scan_serialPorts(baudRate = [9600], cachePath = "../temp/serial.cch", refresh_cache = True)
            dInfo = SerialDevices.find_device("IsWISaS_Controller", [9600], cachePath = "../temp/serial.cch")
            d = SerialDevices.IsWISaS_Controller(dInfo["port"], dInfo["baudRate"], flowCalibration)
        if d.status == 0:
            raise Exception("Failed to connect to IsWISaS Controller")
        
    except:
        port = '80'
        baudRate = 9600
        d = SerialDevices.Mock_IsWISaS_Controller(port, baudRate, flowCalibration)

    print('\n################################')
    

    proSequ = Sequencer.ProbeSequencer("../config/valve.cfg", d)

    root = tk.Tk()
    root.title("IsWISaS_withExternalPiccaro")
    root.geometry("%dx%d+%d+%d"%(1000,850,1,0))

    root.columnconfigure(0, weight=1)
    root.columnconfigure(1, weight=1)
    root.rowconfigure(0, weight=1)

    leftFrame = tk.Frame(root)
    leftFrame.grid(row=0, column=0, sticky="nsew")
    leftFrame.columnconfigure(0, weight=1)
    leftFrame.rowconfigure(0, weight=1)

    rightFrame = tk.Frame(root)
    rightFrame.grid(row=0, column=1, sticky="nsew")    

    tab_parent = ttk.Notebook(rightFrame)

    vf= ValveControlFrame(leftFrame, proSequ, relief=tk.RAISED)
    vf.grid(column=0, row=0, sticky="nsew")

    #pf = PicarroFrame(root, "../config/picarro.cfg")
    #ff = FlowControlFrame(root,  d, flowConfigFile = "../config/flow.cfg", valveReader = pf.valveReader,  relief=tk.RAISED)
    ff = FlowControlFrame(root,  d, flowConfigFile = "../config/flow.cfg", valveReader = None,  relief=tk.RAISED)

    #tab_parent.add(pf, text="Picarro")
    tab_parent.add(ff, text="Flow Control")
    tab_parent.pack(expand=1, fill=tk.BOTH)  
      
    mc = MetaController(vf.sequ, ff, None)
    root.mainloop()
        
