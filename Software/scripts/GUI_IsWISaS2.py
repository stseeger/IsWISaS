import configLoader
import SocketPickle
import SerialDevices
import LogFileReader
import ExtraWidgets

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
    def __init__(self, valves, flow, picarro=None):

        self.valves = valves
        self.flow = flow
        self.picarro = picarro

        valves.metaController = self
        flow.metaController = self
        if not picarro is None:
            picarro.metaController = self
        

        valves.conf["probeType"] = flow.conf["probeType"]
        self.valves.set_currentProbeProfile(0)


class ValveControlFrame(GUI_ValveControl.ValveControlFrame):

    def __init__(self, master, vc, valveConfigFile = "../config/valve.cfg", *args, **kwargs):
        super(ValveControlFrame,self).__init__(master, vc, valveConfigFile, *args, **kwargs)

        self.picarroInfo = None
        
        ExtraWidgets.ToolTip(self.extraLabel, u"Current H\u2082O values from the Picarro\n"+\
                                            u"Left click: enable/disable H\u2082O adapted valve switching") 
        self.after(1500,self.check_Picarro)

    def extraLabel_click(self, event=None):
        self.conf["autoSwitchEnable"] = not (self.conf["autoSwitchEnable"] > 0)

    def refresh_configuration(self):

        # step 1: reload conf for the valve controller
        super(ValveControlFrame, self).refresh_configuration()

        # step 2: reload conf for the flow controller
        freshFlowConf = configLoader.load_confDict(self.metaController.flow.conf["confFile"])
        for key in freshFlowConf["probeType"].keys():
            self.metaController.flow.conf["probeType"][key] = freshFlowConf["probeType"][key]

        self.metaController.flow.fc.set_flowCalibration(freshFlowConf["calibration"])


    def check_Picarro(self):

        try:
            self.picarroInfo = self.metaController.picarro.latestInfo
        except:
            self.picarroInfo = SocketPickle.receive(self.conf["socket_Host"], self.conf["socket_Port"])

        activeCol = ["#c1cdcd", "#bdf"][self.conf["autoSwitchEnable"]>0]

        if not self.picarroInfo is None:

            index = int(self.picarroInfo["H2O"]>=self.conf["H2O_yellowAlert"]) + \
                    int(self.picarroInfo["H2O"]>=self.conf["H2O_redAlert"])

            textCol = "#000"
            if self.picarroInfo["H2O"] <= self.currentProbeProfile["flushTarget_H2O"]: textCol = "#fff"
            if self.picarroInfo["H2O"] >= self.conf["H2O_yellowAlert"]: textCol = "#f80"
            if self.picarroInfo["H2O"] >= self.conf["H2O_redAlert"]: textCol = "#f00"
            
            self.extraLabel.configure(text=u"H\u2082O: " + "%5.0f [ppmV]"%self.picarroInfo["H2O"],
                                      bg = activeCol, fg = textCol)           
            
        else:
            self.extraLabel.configure(text=u"H\u2082O:     no data      ", bg="#ddd", fg="#444")
        
        self.after(1500, self.check_Picarro)
        return
            

    def toggle_flowMode(self, newMode=None, propagate = True):

        super(ValveControlFrame, self).toggle_flowMode(newMode)

        try: id(self.metaController)
        except: return

        if propagate:
            self.metaController.flow.toggle_mode(self.flowMode=="flush", propagate = False)

    def toggle_sequence(self, event=None):
        super(ValveControlFrame, self).toggle_sequence(event)

        try: id(self.metaController)
        except: return
        
        self.metaController.flow.changeFlowRate()

    def set_currentProbeProfile(self, valveIndex=None, name=None):
        super(ValveControlFrame, self).set_currentProbeProfile(valveIndex, name)       

        try: id(self.metaController)
        except: return

        if valveIndex is None: valveIndex = 0
        if name is None: name = self.valveList[valveIndex].name
            
        probeType = self.valves[self.valveToSlotDict[name]]["probeType"]
        x=self.metaController.flow.conf["probeType"][probeType]       

        self.metaController.flow.flushScaleA.set(x["fRateA"])
        self.metaController.flow.flushScaleB.set(x["fRateB"])
        self.metaController.flow.measureScaleA.set(x["mRateA"])
        self.metaController.flow.measureScaleB.set(x["mRateB"])

    def measuredEnough(self):        
        original = super(ValveControlFrame, self).measuredEnough()

        try: id(self.metaController)
        except: return original

        if self.conf["autoSwitchEnable"] < 0 or self.picarroInfo is None:
            return original

        a = self.picarroInfo["stable"]
        b = self.conf["autoSwitchCooldown"] < self.currentDuration()
            
        return original or (a and b)


    def flushedEnough(self):        
        original = super(ValveControlFrame, self).flushedEnough()

        try: id(self.metaController)
        except: return original

        if self.conf["autoSwitchEnable"] < 0 or self.picarroInfo is None:
            return original

        a = self.picarroInfo["H2O"] < self.currentProbeProfile["flushTarget_H2O"]
        b = self.conf["autoSwitchCooldown"] < self.currentDuration()
        
        return original or (a and b)

    def continueSequence(self, skip=False):
        super(ValveControlFrame, self).continueSequence(skip)        

        try: H2O = self.picarroInfo["H2O"]
        except: return
        
        duration = self.currentDuration()

        v1 = (H2O > self.conf["H2O_yellowAlert"]) and self.conf["autoSwitchEnable"]
        v2 = (H2O > self.conf["H2O_redAlert"])    and self.conf["autoSwitchEnable"]
        t  = duration > self.conf["autoSwitchCooldown"]

        if v2 or (v1 and t):

            valveName = self.valves[list(self.valves.keys())[self.activeValve]]["name"]
            print("!!! Wetness alarm! Leaving valve " + valveName)
            self.sequenceButton_click(self.get_nextValve(), True)

        if v2 and t:    
            for v in self.valveList:
                if v.name == valveName:
                    v.stateVar.set(0)
            print("!!!          and disabling it")
    
class FlowControlFrame(GUI_FlowControl.FlowControlFrame):

    def __init__(self, master, fc, flowConfigFile, valveReader, *args, **kwargs):            


        self.valveReader = valveReader
        super(FlowControlFrame,self).__init__(master, fc, flowConfigFile, *args, **kwargs)


    def update(self, selfCalling=True):
        super(FlowControlFrame,self).update(selfCalling)
        self.valveReader.update()
        
        t = self.valveReader.dataBuffer.get_time(timeOffset = -2*time.timezone)
        v = self.valveReader.dataBuffer["ID"]

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

    def toggle_mode(self, newMode=None, propagate = True):        

        super(FlowControlFrame, self).toggle_mode(newMode)
        try: id(self.metaController)
        except: return

        if propagate:
            self.metaController.valves.toggle_flowMode(["measure","flush"][self.isFlushing], propagate = False)

    def on_resize(self, event):        
        self.plotCanvas.on_resize(self.master.winfo_width()-120, self.master.winfo_height()-30)


class PicarroFrame(GUI_Picarro.ValvePicarroFrame):

    def broadcast(self, message):
        pass

if __name__ == "__main__":
        
    # load the flow calibration before initializing the hardware
    flowCalibration = configLoader.load_confDict("../config/flow.cfg")["calibration"]

    # scan all ports to find the one, where the "IsWISaS_Controller" is connected
    #deviceDict, portDict = SerialDevices.scan_serialPorts(9600, "../temp/serial.cch")

    dInfo = SerialDevices.find_device("IsWISaS_Controller", [9600], cachePath = "../temp/serial.cch")
    d = SerialDevices.IsWISaS_Controller(dInfo["port"], dInfo["baudRate"], flowCalibration)
   

    root = tk.Tk()
    root.title("IsWISaS2")
    root.geometry("%dx%d+%d+%d"%(1200,850,1,0))

    tab_parent = ttk.Notebook(root)

    vf = ValveControlFrame(root, d, valveConfigFile = "../config/valve.cfg", relief=tk.RAISED)
    pf = PicarroFrame(root, "../config/picarro.cfg") 
    ff = FlowControlFrame(root,  d, flowConfigFile = "../config/flow.cfg", valveReader = pf.valveReader,  relief=tk.RAISED)

    
    tab_parent.add(pf, text="Picarro")
    tab_parent.add(ff, text="Flow Control")
    

    mc = MetaController(vf, ff, pf)

    dummy1=tk.Frame(root, height=10, width=1200)
    dummy2=tk.Frame(root, height=1, width=1200)
    
    dummy1.grid(row=0, column=0, columnspan=2, sticky="nsew")
    vf.grid(column=0, row=1, sticky="nsew")
    tab_parent.grid(column=1, row=1, sticky="nsew")
    dummy2.grid(row=2, column=0, columnspan=2, sticky="nsew")    
   

    for n in range(3):
        tk.Grid.rowconfigure(root, n, weight=1)
    
    root.mainloop()
        
