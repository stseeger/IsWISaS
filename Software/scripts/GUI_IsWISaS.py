import configLoader
import SocketPickle
import SerialDevices
import LogFileReader
import ExtraWidgets
import const

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
        
        for key in flow.conf["profile"].keys():
            valves.conf["profile"][key] = flow.conf["profile"][key]        


class ValveControlFrame(GUI_ValveControl.ValveControlFrame):

    def __init__(self, master, vc, valveConfigFile = "../config/valve.cfg", *args, **kwargs):
        super(ValveControlFrame,self).__init__(master, vc, valveConfigFile, *args, **kwargs)

        self.picarroInfo = None
        
        ExtraWidgets.ToolTip(self.extraLabel, u"Current H\u2082O values from the Picarro\n"+\
                                            u"Left click: enable/disable H\u2082O adapted valve switching") 
        self.check_Picarro()

    def extraLabel_click(self, event=None):
        self.conf["autoSwitchEnable"] = not (self.conf["autoSwitchEnable"] > 0)

    def refresh_configuration(self):

        # step 1: reload conf for the valve controller
        super(ValveControlFrame, self).refresh_configuration()

        # step 2: reload conf for the flow controller
        freshFlowConf = configLoader.load_confDict(self.metaController.flow.conf["confFile"])
        for key in freshFlowConf["profile"].keys():
            self.metaController.flow.conf["profile"][key] = freshFlowConf["profile"][key]

        self.metaController.flow.fc.set_flowCalibration(freshFlowConf["calibration"])


    def check_Picarro(self):        

        try:
            self.picarroInfo = self.metaController.picarro.latestInfo
        except:
            self.picarroInfo = SocketPickle.receive(self.conf["socket_Host"], self.conf["socket_Port"])       

        if "flushTarget_H2O" in self.currentProbeProfile.keys():

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
        
        self.after(1000, self.check_Picarro)       
            

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

    def set_probeProfile(self, ID=None):
        super(ValveControlFrame, self).set_probeProfile(ID)       

        try: id(self.metaController)
        except: return

        if ID is None: ID = self.activeID
            
        probeType = self.valveDict[ID].probeType
        x=self.metaController.flow.conf["profile"][probeType]       

        self.metaController.flow.flushScaleA.set(x["fRateA"])
        self.metaController.flow.flushScaleB.set(x["fRateB"])
        self.metaController.flow.measureScaleA.set(x["mRateA"])
        self.metaController.flow.measureScaleB.set(x["mRateB"])

    def measuredEnough(self):        
        original = super(ValveControlFrame, self).measuredEnough()
        self.switchCode = const.SWITCH_TIMEOUT

        try: id(self.metaController)
        except:
            self.switchCode = 2
            return original

        if self.conf["autoSwitchEnable"] < 1 or self.picarroInfo is None:
            return original

        a = self.picarroInfo["stable"]
        b = self.conf["autoSwitchCooldown"] < self.currentDuration()

        if a and b: self.switchCode = const.SWITCH_OPTIMUM
        return original or (a and b)


    def flushedEnough(self):        
        original = super(ValveControlFrame, self).flushedEnough()
        self.switchCode = const.SWITCH_TIMEOUT

        try: id(self.metaController)
        except: return original

        if self.conf["autoSwitchEnable"] < 1 or self.picarroInfo is None:
            return original

        a = self.picarroInfo["H2O"] < self.currentProbeProfile["flushTarget_H2O"]
        b = self.conf["autoSwitchCooldown"] < self.currentDuration()

        if a and b: self.switchCode = const.SWITCH_OPTIMUM    
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
            print("!!! Wetness alarm! Leaving valve " + self.activeID)
            self.sequenceButton_click(self.get_nextValve(), True)

        if v2 and t:
            self.valveDict[self.activeID].stateVar.set(0)            
            print("!!!          and disabling it")
    
class FlowControlFrame(GUI_FlowControl.FlowControlFrame):

    def __init__(self, master, fc, flowConfigFile, valveReader, *args, **kwargs):            


        self.valveReader = valveReader
        super(FlowControlFrame,self).__init__(master, fc, flowConfigFile, *args, **kwargs)


    def update(self, selfCalling=True):
        super(FlowControlFrame,self).update(selfCalling)
        self.valveReader.update()

        try:
            timeOffset = self.metaController.picarro.conf["valveTimeOffset"]*3600-time.timezone
        except:
            timeOffset = -time.timezone
        
        t = self.valveReader.dataBuffer.get_time(timeOffset = timeOffset)
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
    root.title("IsWISaS")
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

    vf = ValveControlFrame(leftFrame, d, valveConfigFile = "../config/valve.cfg", relief=tk.RAISED)
    vf.grid(column=0, row=0, sticky="nsew")

    pf = PicarroFrame(root, "../config/picarro.cfg")
    ff = FlowControlFrame(root,  d, flowConfigFile = "../config/flow.cfg", valveReader = pf.valveReader,  relief=tk.RAISED)

    tab_parent.add(ff, text="Flow Control")
    tab_parent.add(pf, text="Picarro")
    tab_parent.pack(expand=1, fill=tk.BOTH)  
      
    mc = MetaController(vf, ff, pf)
    root.mainloop()
        
