import tkinter as tk
from tkinter import ttk
from tkinter import font as tkFont
import datetime
import time
import PlotCanvas
import os
import DataBuffer
import configLoader

colors = configLoader.load_confDict("../config/default/colors.cfg")

def secs2DateString(seconds_POSIX, stringFormat = "%m-%d/%H:%M:%S"):
    return time.strftime(stringFormat,time.gmtime(seconds_POSIX))

class Valve():
    def __init__(self, name, probeType, slot, index, button, checkbox=None, stateVar=None):
        self.name  = name
        self.probeType = probeType
        self.slot  = int(slot)
        self.index = int(index)
        self.button = button
        self.checkbox = checkbox
        self.stateVar = stateVar

    def grid(self, row, column):
        self.button.grid(row=row, column=column, sticky = "nsew")
        if not self.checkbox is None:
            self.checkbox.grid(row=row+1, column=column)
            self.checkbox.select()

    def __repr__(self):
        return("<\"%s\"(%s; slot %s)>"%(self.name, self.probeType, self.slot))
        

class ValveControlFrame(tk.Frame):
    def __init__(self, master, vc, logfilePath, *args, **kwargs):
        super(ValveControlFrame,self).__init__(master, *args, **kwargs)

        self.master = master
        self.vc=vc
        self.conf = configLoader.load_confDict("../config/valve.cfg")
        self.valves = self.conf["valve"]

        buffPar = DataBuffer.Parameter(name = "ID", unit = "active valve")
        self.valveBuffer = DataBuffer.Buffer(100, self.conf["logFile"], parameters = buffPar)                                                                                    

        self.font = tkFont.Font(family="Sans", size=7, weight="bold")

        # create basic frames for layout
        self.buttonFrame = tk.Frame(self, width=640)
        self.buttonFrame.pack(side=tk.TOP, fill=tk.X)
        #self.buttonFrame.config(bg="red")

        self.buttonFrame2 = tk.Frame(self, width=640)
        self.buttonFrame2.pack(side=tk.TOP, fill=tk.X)
        #self.buttonFrame2.config(bg="blue")

        self.lowerFrame = tk.Frame(self)
        self.lowerFrame.pack(side=tk.BOTTOM, expand=1, fill=tk.BOTH)
        self.lowerFrame.config(bg="#ccc")
        tk.Label(self.lowerFrame, text="Space for extensions").pack(side=tk.TOP)

        self.activeValve = 1
        self.sequencePosition = -1
        self.flowMode = "flush"
        self.sequMode = "inactive"
        self.startTime = 0

        #--------------------------------------------------------------
        if not vc.check_status():
            self.infoFrame = tk.Frame(master)
            self.infoFrame.place(relheight=1, relwidth=1, x=0, y=0)
            self.infoFrame.config(bg="#fbb")
            tk.Button(self.infoFrame, command=self.hide_infoFrame,
                      text="No valve controller connected\n Click to proceed without functional valve controller").pack(side=tk.TOP)

        # ---- create valve control buttons ---- for all valves -------
        self.valveList = []
        self.valveToSlotDict = {}
        self.valveToIndexDict = {}

        n = -1
        for i,valveSlot in enumerate(self.valves.keys()):

            valveName = self.valves[valveSlot]["name"]
            probeType = self.valves[valveSlot]["probeType"]
            if not len(valveName):
                continue

            n+=1

            self.valveToIndexDict[valveName] = n
            self.valveToSlotDict[valveName] = valveSlot
            
            tk.Grid.columnconfigure(self.buttonFrame, n, weight=1)

            button = tk.Button(self.buttonFrame, command = lambda j = n: self.valveButton_click(j),
                               font = self.font, text = ("%d\n"%(i+1))+valveName, height = 2)

            stateVar = tk.IntVar()
            checkbox = tk.Checkbutton(self.buttonFrame, text="", variable=stateVar,
                                      command = self.update_valveButtons, relief=tk.FLAT)
           
            self.valveList.append(Valve(valveName, probeType, valveSlot, n, button, checkbox, stateVar))
            self.valveList[-1].grid(row=0, column=n)
                         
            

        # ---- create valve sequence buttons -----------
        self.valveSequence = []
        
        for i in range(len(self.conf["sequence"])):

            valveName = self.conf["sequence"][i]
            valveSlot = self.valveToSlotDict[valveName]
            
            probeType = self.valves[valveSlot]["probeType"]
            
            tk.Grid.columnconfigure(self.buttonFrame2, i+1, weight=1)
            
            button = (tk.Button(self.buttonFrame2, command = lambda j = i: self.sequenceButton_click(j),
                                font = self.font, text = self.conf["sequence"][i], height = 1))

            stateVar = tk.IntVar()
            checkbox = tk.Checkbutton(self.buttonFrame2, text="",variable=stateVar,
                                      command = self.update_valveButtons, relief=tk.FLAT)

            self.valveSequence.append(Valve(valveName, probeType, valveSlot, i, button, checkbox, stateVar))
            self.valveSequence[-1].grid(row=0, column=i+1)  

        #------ sequence start stop button--------------------------------
        self._sequenceButtonImages = []
        for name in ["start_32", "stop_32", "hourglass_32"]:
            try:
                image = tk.PhotoImage(file="images/"+name+".gif")
            except:
                image = None
            self._sequenceButtonImages.append(image)
            
        buttonFont = tkFont.Font(family="Sans", weight="bold")
        self.sequenceButton = tk.Button(self.buttonFrame2, command=self.toggle_sequence, 
                                        text="start\nsequence" , font=buttonFont,
                                        image=self._sequenceButtonImages[0])
        self.sequenceButton.grid(row=0, column=0, rowspan=2, sticky="nsew")

        colors["neutralButton"] = self.sequenceButton.cget("bg")

        #-------- progress bars ------------------------------------------
        self.progressFrame = tk.Frame(self.buttonFrame2, height = 20, width=self.winfo_width()-100)        
        self.progressFrame.grid(row=2, columnspan = len(self.valveSequence)+1)
        self.progBars = {}

        for mode, side, anchor in [("flush", 'left','w'),("measure", 'right', 'e')]:            
            style = ttk.Style()
            style.configure("%s.Horizontal.TProgressbar"%mode, background=colors[mode])
            progBar = ttk.Progressbar(self.progressFrame, style="%s.Horizontal.TProgressbar"%mode, maximum = 50, mode = 'determinate')
            label   = tk.Label(progBar, text=u"\u221e", bg=colors[mode])
            label.place(relx=0.5,rely=0)
            #progBar.pack(side=side,anchor=anchor, expand=2, fill=tk.BOTH)
            progBar.pack(side=side,anchor=anchor, expand=2, fill=tk.BOTH)

            self.progBars[mode] = {"bar": progBar, "label":label}


        self._job = None
        self.sequencePaused = False

        # open first valve of valveSequence
        #time.sleep(1)
        self.sequenceButton_click(0)
        self.sequencePosition = -1
        time.sleep(0.2)
        self.sequenceButton_click(0)
        #self.sequenceButton_click(0,False)

    #================================================================================

    def hide_infoFrame(self, event=None):
        self.infoFrame.place_forget()

    def set_currentProbeProfile(self, valveIndex=None, name=None):

        if name is None:
            name = self.valveList[valveIndex].name
            
        probeType = self.valves[self.valveToSlotDict[name]]["probeType"]
        try:
            x=self.conf["probeType"][probeType]
        except:
            print("Missing specifications for probe type \"%s\", resorting to default specifications"%probeType)
            x=self.conf["probeType"]["default"]

        for key in ["fRateA","fRateB","mRateA","mRateB"]:
            if not key in x.keys():
                x[key] = 0        

        self.currentProbeProfile = x.copy()
        self.currentProbeProfile["duration"] = self.currentProbeProfile["fDuration"] + self.currentProbeProfile["mDuration"]


    def toggle_flowMode(self, newMode=None):
        if newMode is None:
            newMode = ["measure","flush"] [self.flowMode=="measure"]

        change =  not self.flowMode == newMode

        self.flowMode = newMode

        if change:
            print("toggle to %s mode"%newMode)
            if newMode == "flush":
                self.startTime = time.time()        

    def toggle_sequence(self, event=None):

        if not self._job is None:
            self.after_cancel(self._job)
            self._job = None

        if not self.sequMode == "active":
            self.sequMode = "active"
            self.sequenceButton.config(image=self._sequenceButtonImages[1], text="stop\nsequence")
            self._job = self.after(10, self.continueSequence)
            self.startTime = time.time()
        else:
            self.sequMode = "inactive"
            self.sequenceButton.config(image=self._sequenceButtonImages[0], text="start\nsequence")

        print("---toggle sequence---")
        self.update_valveButtons()
        self.update_progressBars()


    def currentDuration(self):
        return time.time()-self.startTime + 0.0001

    def flushedEnough(self):        
        return (self.flowMode == "flush") and (self.currentDuration() >= self.currentProbeProfile["fDuration"])

    def measuredEnough(self):
        return (self.flowMode == "measure") and (self.currentDuration() >= self.currentProbeProfile["mDuration"])

    def continueSequence(self):

        nowTime = time.time()

        if self.flushedEnough():
            self.toggle_flowMode()
            self.update_valveButtons()
            self.startTime = time.time()

        if self.measuredEnough():    
            for nextPos in list(range(self.sequencePosition+1, len(self.valveSequence))) + list(range(0, self.sequencePosition)) + [self.sequencePosition]:                
                if self.valveSequence[nextPos].stateVar.get():
                    break
                else:
                    print("skip deactivated", self.valveSequence[nextPos])
            self.sequenceButton_click(nextPos, True)

        
        self._job = self.after(500, self.continueSequence)
        self.update_progressBars(self.currentDuration())
        

    def sequenceButton_click(self, sequencePos, withinSequence=False):
        noChange = self.sequencePosition==sequencePos
        self.sequencePosition = sequencePos

        # activate the corresponding valve button to an active button in the valve sequence
        for i, valve in enumerate(self.valveList):
            if valve.name == self.valveSequence[sequencePos].name:
                self.activeValve=i
                break
        
        self.open_valve(self.valveSequence[sequencePos].name, noChange, withinSequence)

    def valveButton_click(self, position):
        sequencePos = -1 # clicking directly on a valve button discards the current position within the sequence
        noChange = self.activeValve == position and self.sequencePosition == sequencePos
        self.activeValve = position
        self.sequencePosition = sequencePos        
        self.open_valve(self.valveList[position].name, noChange)


    def update_valveButtons(self):

        bgColor = colors["active"]
        if self._job is None:
            if self.sequencePaused:
                bgColor = colors["paused"]
            else:
                bgColor = colors["static"]

        self.buttonFrame.config(bg=bgColor)
        self.buttonFrame2.config(bg=bgColor)

        buttonColors = [colors["neutralButton"], colors[self.flowMode]]
        for n,buttonList in enumerate([self.valveList, self.valveSequence]):            
            for i, button in enumerate(buttonList):
                index = [i==self.activeValve, i==self.sequencePosition][n]
                button.button.config(bg=[buttonColors[index]], relief = [tk.RAISED, tk.GROOVE][index])
                button.checkbox.config(bg=colors["neutralButton"])
                
                # deactivate button on the valveSequence level, when the corresponding valve button
                # has been deactivated
                if n == 1:
                    baseValveState = self.valveList[self.valveToIndexDict[button.name]].stateVar.get()
                    button.stateVar.set(button.stateVar.get() and baseValveState)
               

                button.button.config(state = [tk.DISABLED, tk.NORMAL][button.stateVar.get()])

    def update_progressBars(self,duration=0):


        flushDuration = self.currentProbeProfile["fDuration"]        
        measureDuration = self.currentProbeProfile["mDuration"]

        if duration:           
            self.progBars[self.flowMode]["bar"].configure(value=duration)
            maxDuration = self.currentProbeProfile[["mDuration","fDuration"][self.flowMode=="flush"]]
            self.progBars[self.flowMode]["label"].configure(text = "%.0f/%.0f"%(duration,maxDuration))
        else:            
            self.master.update()
            w = self.master.winfo_width()
            r = self.currentProbeProfile["fDuration"]/self.currentProbeProfile["duration"]            
            for flowMode, length in [("flush", w*r),("measure",w*(1-r))]:                
                maxDuration = self.currentProbeProfile[["mDuration","fDuration"][flowMode=="flush"]]
                self.progBars[flowMode]["bar"].configure(value=0, max=maxDuration, length=length)
                self.progBars[flowMode]["label"].configure(text = "%.0f/%.0f"%(duration,maxDuration))

    def open_valve(self, valveName, noChange=False, withinSequence=False):        

        if self.sequMode == "active" and not withinSequence:
            self.toggle_sequence()

        if noChange:
            self.toggle_flowMode()            
            
        else:
            print("------------------\nactive probe: "+str(self.valveList[self.valveToIndexDict[valveName]]))
            self.toggle_flowMode("flush")
            self.vc.set_valve(int(self.valveToSlotDict[valveName]))
            self.set_currentProbeProfile(name=valveName)
            self.valveBuffer.add(valveName)
            
        self.update_valveButtons()
        self.update_progressBars()

        return


if __name__ == "__main__":
    import SerialDevices
    deviceDict, portDict = SerialDevices.scan_serialPorts(9600)
    if "IsWISaS_Controller" in deviceDict.keys():        
        vc = SerialDevices.IsWISaS_Controller(deviceDict["IsWISaS_Controller"].port, deviceDict["IsWISaS_Controller"].baudRate)
    else:
        vc = SerialDevices.ValveController("foobar", 0)

    root = tk.Tk()
    root.title("ValveController")
    root.geometry("%dx%d+%d+%d"%(800,150,1,0))
    g = ValveControlFrame(root, vc, "../log/%s.vlg"%secs2DateString(time.time(), "%Y%m%d%H%M%S"), relief=tk.RAISED)
    g.pack(fill=tk.BOTH, expand=1)
    root.mainloop()
        
        
