import configLoader
import SerialDevices
import LogFileReader

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
    def __init__(self, valves, flow, measurement):

        valves.metaController = self
        flow.metaController = self
        
        self.valves = valves
        self.flow = flow
        self.measurement = measurement

        valves.conf["probeType"] = flow.conf["probeType"]
        self.valves.set_currentProbeProfile(0)


class ValveControlFrame(GUI_ValveControl.ValveControlFrame):

    def toggle_flowMode(self, newMode=None):        
        super(ValveControlFrame, self).toggle_flowMode(newMode)

        try: id(self.metaController)
        except: return

        self.metaController.flow.toggle_mode(self.flowMode=="flush")

    def toggle_sequence(self, event=None):
        super(ValveControlFrame, self).toggle_sequence(event)
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
        a = self.metaController.measurement.conf["autoSwitchEnable"] > 0
        b = self.metaController.measurement.conf["autoSwitchCooldown"] <= self.currentDuration()
        c = self.metaController.measurement.is_stable
        return  original or(a and b and c)

    def flushedEnough(self):        
        original = super(ValveControlFrame, self).flushedEnough()
        a = self.metaController.measurement.conf["autoSwitchEnable"] > 0
        b = self.metaController.measurement.conf["autoSwitchCooldown"] <= self.currentDuration()
        c = (self.flowMode == "flush") and self.metaController.measurement.current["H2O"] < self.currentProbeProfile["flushTarget_H2O"]
        return  original or (a and b and c)

    def continueSequence(self):
        super(ValveControlFrame, self).continueSequence()

        try: id(self.metaController)
        except: pass

        H2O = self.metaController.measurement.current["H2O"]
        duration = self.currentDuration()

        thresholds = self.metaController.measurement.conf["dangerThresholds_H2O"]
        toleranceSeconds = self.metaController.measurement.conf["dangerToleranceSeconds"]

        H2O_dangerLevel = 0
        for i in range(len(thresholds)):
            if H2O > thresholds[i] and duration > toleranceSeconds[i]:
                H2O_dangerLevel=i+1

        valveName = self.valves[list(self.valves.keys())[self.activeValve]]["name"]
        warning = "!!! Wetness alarm! Leaving valve " + valveName
        
        if H2O_dangerLevel == len(thresholds):            
            for v in self.valveList:
                if v.name == valveName:
                    v.stateVar.set(0)
            warning = warning + " and disabling it"            

        if H2O_dangerLevel >= len(thresholds)-1:            
            self.sequenceButton_click(self.get_nextValve(), True)
            print(warning)


            

    
class FlowControlFrame(GUI_FlowControl.FlowControlFrame):

    def on_resize(self, event):
        self.plotCanvas.on_resize(self.master.winfo_width()-160, self.master.winfo_height()-30)


class PicarroFrame(GUI_Picarro.PicarroFrame):

    def on_resize(self,event):
        width = self.master.winfo_width()
        height = self.master.winfo_height()
        for i in range(len(self.parList)):
            self.parCanvas[i].on_resize(width-100,(height-10)/len(self.parList)-10) 


if __name__ == "__main__":

    # load the picarro configuration file
    picarro = configLoader.load_confDict("../config/picarro.cfg")

    for picarroLogDir in picarro["rawLogSearchPaths"]:
        if os.path.exists(picarroLogDir):
            break
        
    # load the flow calibration before initializing the hardware
    flowCalibration = configLoader.load_confDict("../config/flow.cal")["calibration"]

    # scan all ports to find the one, where the "IsWISaS_Controller" is connected
    deviceDict, portDict = SerialDevices.scan_serialPorts(9600)
    if "IsWISaS_Controller" in deviceDict.keys():        
        d = SerialDevices.IsWISaS_Controller(deviceDict["IsWISaS_Controller"].port, deviceDict["IsWISaS_Controller"].baudRate, flowCalibration)
    else:
        d = SerialDevices.IsWISaS_Controller("foobar", 0)

    # initialize the LogFileReader
    configFile = "../config/logDescriptors/picarroLxxxx-i.lgd"
    picarroLogFileReader = LogFileReader.Reader(configFile, picarroLogDir)
    picarroLogFileReader.fill_dataBuffer()

    root = tk.Tk()
    root.title("IsWISaS Control Interface")
    root.geometry("%dx%d+%d+%d"%(1200,800,1,0))

    tab_parent = ttk.Notebook(root)

    valveLogFile = "../log/%s.vlg"%secs2DateString(time.time(), "%Y%m%d%H%M%S")

    vf = ValveControlFrame(root, d, valveLogFile, valveConfigFile = "../config/valve.cfg", relief=tk.RAISED)
    ff = FlowControlFrame(tab_parent,  d, flowConfigFile = "../config/flow.cfg",  relief=tk.RAISED)
    pf = PicarroFrame(tab_parent, picarroLogFileReader, picarro)

    mc = MetaController(vf, ff, pf)

    pf.pack(fill=tk.BOTH, expand=1)
    vf.pack(fill=tk.BOTH, expand=1)

    tab_parent.add(pf, text="Piacrro measurements")
    tab_parent.add(ff, text="Flow Control")
    tab_parent.pack(expand=1, fill="both")
    
    #ff.pack(fill=tk.BOTH)

    root.mainloop()
        
