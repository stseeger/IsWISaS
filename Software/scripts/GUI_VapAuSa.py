import configLoader
import SocketPickle
import SerialDevices
import LogFileReader
import ExtraWidgets
import const

import Sequencer
import GUI_ValveControl
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
        if not flow is None:
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
        self.sequ.picarroInfo = self.sequ.metaController.picarro.latestInfo
        

class PicarroFrame(GUI_Picarro.ValvePicarroFrame):

    def broadcast(self, message):
        pass
        #super(PicarroFrame).broadcast(message)        

if __name__ == "__main__":
        
    # load the flow calibration before initializing the hardware
    flowCalibration = configLoader.load_confDict("../config/flow.cfg")["calibration"]
    colors = configLoader.load_confDict("../config/default/colors.cfg")


    print('################################')
    print('Connecting to IsWISaS_Controller...')

    # scan all ports to find the one, where the "IsWISaS_Controller" is connected
    #deviceDict, portDict = SerialDevices.scan_serialPorts(9600, "../temp/serial.cch")

    dInfo = SerialDevices.find_device("Bagsampler", [9600], cachePath = "../temp/serial.cch")

    try:
        d = SerialDevices.IsWISaS_Controller(dInfo["port"], dInfo["baudRate"], flowCalibration)
        if d.status == 0:
            print("Device not found at the cached serial port...")
            deviceDict, portDict = SerialDevices.scan_serialPorts(baudRate = [9600], cachePath = "../temp/serial.cch", refresh_cache = True)
            dInfo = SerialDevices.find_device("Bagsampler", [9600], cachePath = "../temp/serial.cch")
            d = SerialDevices.IsWISaS_Controller(dInfo["port"], dInfo["baudRate"], flowCalibration)
        if d.status == 0:
            raise Exception("Failed to connect to IsWISaS Controller")
        
    except:
        port = '80'
        baudRate = 9600
        d = SerialDevices.Mock_IsWISaS_Controller(port, baudRate, flowCalibration)

    print('\n################################')
   
    root = tk.Tk()
    root.title("Bagsampler")
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

    pf = PicarroFrame(root, "../config/picarro.cfg")    

    proSequ = Sequencer.ProbeSequencer("../config/valve.cfg", d)
    vf= ValveControlFrame(leftFrame, proSequ, relief=tk.RAISED)
    vf.grid(column=0, row=0, sticky="nsew")

    tab_parent.add(pf, text="Picarro")    
    tab_parent.pack(expand=1, fill=tk.BOTH)  
      
    mc = MetaController(vf.sequ, None, pf)
    
    root.mainloop()
        
