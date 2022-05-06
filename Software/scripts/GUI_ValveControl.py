import tkinter as tk
from tkinter import ttk
from tkinter import font as tkFont
import time
import collections
import math

import configLoader
import Sequencer
import const
import ExtraWidgets

MAX_VALVES_PER_COLUMN = const.MAX_VALVES_PER_COLUMN
colors = configLoader.load_confDict("../config/default/colors.cfg",
                                    verbose = __name__=="__main__")
class ValveControlFrame(tk.Frame):
    def __init__(self, master, probeSequencer, *args, **kwargs):
        super(ValveControlFrame,self).__init__(master, *args, **kwargs)

        self.master = master        
        self.sequ = probeSequencer        
        
        self.probeButtonFrame = tk.Frame(self)        
        self.probeButtonFrame.grid(row=0, column=0, sticky="new")

        self.progressFrame = tk.Frame(self)        
        self.progressFrame.grid(row=1, column=0, sticky="nsew")


        #--------------------------
        # create basic frames for layout
        self.probeButtonFrame = tk.Frame(self)
        self.probeButtonFrame.grid(row=0, column=0, sticky="nsew")

        self.rightFrame = tk.Frame(self)       
        self.rightFrame.grid(row=0, column=1, columnspan=2, sticky="nsew")

        self.rowconfigure(0, weight=1)        
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)

        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)

    
        # ---- right frame (mainly valve sequence)------------- -----------

        self.rightFrame.rowconfigure(0, weight=0)
        self.rightFrame.rowconfigure(1, weight=5)        
        self.rightFrame.columnconfigure(0, weight=1)        

        self.upperRightFrame = tk.Frame(self.rightFrame)
        self.upperRightFrame.grid(row=0, column=0, sticky="nsew")
        self.upperRightFrame.rowconfigure(0, weight=1)
        self.upperRightFrame.columnconfigure(0, weight=1)
        self.upperRightFrame.columnconfigure(1, weight=3)
        self.upperRightFrame.columnconfigure(2, weight=1)

        self.lowerRightFrame = tk.Frame(self.rightFrame)
        self.lowerRightFrame.grid(row=1, column=0, sticky="nsew")
        self.lowerRightFrame.rowconfigure(0, weight=1)        
        self.lowerRightFrame.columnconfigure(0, weight=0)
        self.lowerRightFrame.columnconfigure(1, weight=1)

        self.progressFrame = tk.Frame(self.lowerRightFrame)        
        self.progressFrame.grid(row=0, column=0, sticky="nsew")

        self.sequenceFrame = tk.Frame(self.lowerRightFrame)
        self.sequenceFrame.grid(row=0, column=1, sticky="nsew")        
        self.sequenceFrame.rowconfigure(1, weight=1)
        self.sequenceFrame.columnconfigure(0, weight=1)

        self.sequenceControlFrame = tk.Frame(self.sequenceFrame)
        self.sequenceControlFrame.grid(row=0, column=0, sticky="nsew")
        self.sequenceControlFrame.columnconfigure(0, weight=1)
        self.sequenceControlFrame.columnconfigure(1, weight=2)

        self.sequenceButtonFrame = tk.Frame(self.sequenceFrame)
        self.sequenceButtonFrame.grid(row=1, column=0, sticky="nsew")

        # test buttons

        self.b_alarm = tk.Button(self, text='no alarm', command=self.alarmTest)
        self.b_dry   = tk.Button(self, text='not dry', command=self.dryTest)
        self.b_stable= tk.Button(self, text='not stable', command=self.stableTest)

        self.b_alarm.grid( row=2, column=0, sticky='nsew')
        self.b_dry.grid(   row=2, column=1, sticky='nsew')
        self.b_stable.grid(row=2, column=2, sticky='nsew')

        # ------------ create valve control buttons -------------------
        self.fill_probeButtonFrame()      

        #-------- schedule, status and refresh -----------------------------
        self._scheduleButtonImage = tk.PhotoImage(file="../images/time_24.gif")
        self.scheduleButton = tk.Button(self.upperRightFrame, text="Schedule", image= self._scheduleButtonImage, command=self.schedule, width=24)
        self.scheduleButton.grid(row=0, column=0, sticky="nsew")
        ExtraWidgets.ToolTip(self.scheduleButton, u"To be implemented...")

        self.extraLabel = tk.Label(self.upperRightFrame, text="~~~~~~~~~~~", bg='#ddd')
        self.extraLabel.grid(row=0, column=1, sticky='nsew')
        self.extraLabel.bind("<Button-1>", self.extraLabel_click)

        self._refreshButtonImage = tk.PhotoImage(file="../images/refresh_16.gif")
        self.refreshButton = tk.Button(self.upperRightFrame, text="Refresh", image= self._refreshButtonImage, command=self.refresh_configuration)
        self.refreshButton.grid(row=0, column=2, sticky="nsew")
        ExtraWidgets.ToolTip(self.refreshButton, u"Reload flow profiles (from flow.cfg) and H\u2082O thresholds (from valve.cfg)\n"+\
                                                  "Changing the logfile path requires a restart")

        #----- sequence buttons --------------------------------------

        self.valveSequence = self.fill_sequenceButtonFrame()

        #------ sequence control buttons--------------------------------
        self._sequenceButtonImages = []
        for name in ["start_32", "stop_32", "next_32", "hourglass_32"]:
            try:
                image = tk.PhotoImage(file="../images/"+name+".gif")
            except:
                image = None
            self._sequenceButtonImages.append(image)

        buttonFont = tkFont.Font(family="Sans", weight="bold")
        self.b_sequenceToggle = tk.Button(self.sequenceControlFrame, command=self.toggle_sequence, 
                                        text="stop\nsequence" , font=buttonFont,
                                        image=self._sequenceButtonImages[1])                                                    

        self.b_sequenceNext = tk.Button(self.sequenceControlFrame, command= lambda: self.skip_sequence(skip=True),
                                        text="skip\nprobe" , font=buttonFont,
                                        image=self._sequenceButtonImages[2])
        
        self.b_sequenceToggle.grid(row=0, column=0, sticky="nsew")        
        self.b_sequenceNext.grid(row=0, column=1, sticky="nsew")
            
        ExtraWidgets.ToolTip(self.b_sequenceToggle, text="Start/Stop the valve sequence\nThe seuquence goes from left to right and from top to bottom")
        ExtraWidgets.ToolTip(self.b_sequenceNext, text="Continue with the valve in the sequence")

        colors["neutralButton"] = self.b_sequenceToggle.cget("bg")

        #-------- progress bars ------------------------------------------
        
        self.progBars = {}

        for mode, side, anchor in [("flush", 'bottom','n'),("measure", 'top', 's')]:            
            style = ttk.Style()
            style.configure("%s.Vertical.TProgressbar"%mode, background=colors[mode])
            progBar = ttk.Progressbar(self.progressFrame, style="%s.Vertical.TProgressbar"%mode, orient=tk.VERTICAL, maximum = 50, mode = 'determinate')
            label   = tk.Label(progBar, text=u"\u221e", bg=colors[mode],wraplength=1)
            label.place(relx=0.2,rely=0.5)            
            progBar.pack(side=side,anchor=anchor, expand=2, fill=tk.BOTH)

            self.progBars[mode] = {"bar": progBar, "label":label}

        self.reset_progressBars()
        self._job = self.after(500, self.update)
       

    #---------------------------------------------   
    def fill_probeButtonFrame(self):

        for button in self.probeButtonFrame.grid_slaves():
            button.destroy()

        probeDict = self.sequ.probeDict
        self.probeButtonDict = {}

        N = len(probeDict.keys())
        columnCount = math.ceil(N/MAX_VALVES_PER_COLUMN)
        rowCount = math.ceil(N/columnCount)
        
        
        for i, ID in enumerate(probeDict.keys()):
            buttonState = tk.ACTIVE if probeDict[ID].isActive() else tk.DISABLED
            button = tk.Button(self.probeButtonFrame, command = lambda j = i: self.valveButton_click(j),
                               font = tkFont.Font(family="Sans", size=9, weight="bold"),
                               text = ID, disabledforeground="#866",state = buttonState)
            button.bind('<Button-3>', self.rightClickProbe)

            self.probeButtonDict[self.probeButtonFrame.nametowidget(button)] = {"ID":ID, "button":button}            
            
            row = math.floor(i/columnCount)
            column = i-math.floor(row*columnCount)
            button.grid(row = row, column=column, sticky="nsew")
            self.probeButtonFrame.rowconfigure(row, weight=1)
            self.probeButtonFrame.columnconfigure(column, weight=1)

    #---------------------------------------------
    def fill_sequenceButtonFrame(self):

        for button in self.sequenceButtonFrame.grid_slaves():
            button.destroy()

        probeDict = self.sequ.probeDict
        sequence = self.sequ.sequence
        self.sequenceButtonDict = {}
        
        N = len(sequence)
        columnCount = math.ceil(N/MAX_VALVES_PER_COLUMN)
        rowCount = math.ceil(N/columnCount)
        
        for i, item in enumerate(sequence):           
            buttonState = tk.ACTIVE #if (sequence[i].isActive() and probeDict[ID].isActive()) else tk.DISABLED
            button = (tk.Button(self.sequenceButtonFrame, command = lambda j = i: self.sequenceButton_click(j),
                                font = tkFont.Font(family="Sans", size=9, weight="bold"),text = item.ID,state = buttonState))
            button.bind('<Button-3>', self.rightClickSequence)

            self.sequenceButtonDict[self.probeButtonFrame.nametowidget(button)] = {"position":i, "button":button}            
            
            row = math.floor(i/columnCount)
            column = i-math.floor(row*columnCount)
            button.grid(row=row, column=column, sticky="nsew")
            self.sequenceButtonFrame.rowconfigure(row, weight=1)
            self.sequenceButtonFrame.columnconfigure(column, weight=1)

    #-----------------------------------------------------------

    def alarmTest(self):
        self.sequ._alarmed = not self.sequ._alarmed
        self.b_alarm.config(text=["ALARM", "no alarm"][1-self.sequ._alarmed], bg=["#f00",colors["neutralButton"]][1-self.sequ._alarmed])

    def dryTest(self):
        self.sequ._dry = not self.sequ._dry
        self.sequ.picarroInfo={"H2O":20000}
        self.b_dry.config(text=["DRY", "not dry"][1-self.sequ._dry], bg=["#fff",colors["neutralButton"]][1-self.sequ._dry])

    def stableTest(self):
        self.sequ._stable = not self.sequ._stable
        self.b_stable.config(text=["STABLE", "instable"][1-self.sequ._stable], bg=["#66f",colors["neutralButton"]][1-self.sequ._stable])

    def refresh_configuration(self):
        self.sequ.load_conf()
        self.fill_sequenceButtonFrame()
        self.fill_probeButtonFrame()

    def schedule(self):
        pass

    def extraLabel_click(self,event):
        pass

    def valveButton_click(self, i):        
        clickID = list(self.sequ.probeDict.keys())[i]
        self.sequ.toggle(enabled=False)
        if clickID == self.sequ.activeProbe.ID:
            self.sequ.toggle_activeProbeMode(switchCode = const.SWITCH_MANUAL)
        else:
            self.sequ.switch_probe(clickID, switchCode = const.SWITCH_MANUAL)

    def sequenceButton_click(self, i):

        if i == self.sequ.position:
            self.sequ.toggle_activeProbeMode(switchCode = const.SWITCH_MANUAL)
        else:            
            self.sequ.switch_sequence(i, switchCode = const.SWITCH_MANUAL)

    def rightClickProbe(self, event):

        # retrieve probe ID and button pointer
        buttonInfo = self.probeButtonDict[event.widget]
                
        # toggle
        probe = self.sequ.probeDict[buttonInfo["ID"]]
        probe.toggle_activity()
        buttonInfo["button"]["state"] = tk.ACTIVE if probe.isActive() else tk.DISABLED

    def rightClickSequence(self, event):

        # retrieve probe ID and button pointer
        buttonInfo = self.sequenceButtonDict[event.widget]                       
        sequItem = self.sequ.sequence[buttonInfo["position"]]        

        if self.sequ.probeDict[sequItem.ID].isActive():
            sequItem.toggle_activity()        
            buttonInfo["button"].config(state= tk.ACTIVE if sequItem.isActive() else tk.DISABLED)

    def toggle_sequence(self):
        self.sequ.toggle()
        if self.sequ.isActive():
            probeID = self.sequ.sequence[self.sequ.position].ID
            self.sequ.switch_probe(probeID, switchCode = const.SWITCH_MANUAL)

    def toggle_mode(self):
        self.sequ.activeProbe.toggle_mode(switchCode = const.SWITCH_MANUAL)
        self.update()
        

    def skip_sequence(self, skip=False):
        activeProbe = self.sequ.update(skip)
        self.update()
        self.reset_progressBars()


    def update_buttons(self):       

        for key in self.sequenceButtonDict.keys():
            position = self.sequenceButtonDict[key]["position"]            
            button = self.sequenceButtonDict[key]["button"]
            probeID = self.sequ.sequence[position].ID

            isActive = self.sequ.probeDict[probeID].isActive() and self.sequ.sequence[position].isActive()

            activeColor = colors[self.sequ.activeProbe.mode]
            if position == self.sequ.position:
                color = colors[self.sequ.activeProbe.mode] if self.sequ.isActive() else "#999"
            else:
                color = colors["neutralButton"]

            state = tk.NORMAL if isActive else tk.DISABLED
            fg = "#007" if self.sequ.isActive() else "#944"
            
            button.config(state= state, bg=color, fg=fg)

        for key in self.probeButtonDict.keys():
            probeID = self.probeButtonDict[key]["ID"]
            button = self.probeButtonDict[key]["button"]

            state = tk.NORMAL if self.sequ.probeDict[probeID].isActive() else tk.DISABLED
            activeColor = colors[self.sequ.activeProbe.mode]
            color = activeColor if probeID == self.sequ.activeProbe.ID else colors["neutralButton"]

            button.config(state= state, bg=color)

        if self.sequ.isActive():
            self.b_sequenceToggle.config(image=self._sequenceButtonImages[1], text="stop\nsequence")
        else:
            self.b_sequenceToggle.config(image=self._sequenceButtonImages[0], text="start\nsequence")
            

    def update(self):        
        
        activeProbe = self.sequ.activeProbe

        if self.sequ.isActive():
            self.sequ.update()

            if not activeProbe == self.sequ.activeProbe:
                self.reset_progressBars()
                activeProbe = self.sequ.activeProbe
                
            else:
                self.update_progressBars()

        self.update_buttons()        

        #----
        if not self.sequ.picarroInfo is None:

            activeCol = ["#c1cdcd", "#bdf"][self.sequ.conf["autoSwitchEnable"]>0]            

            textCol = "#000"
            currentProbeProfile = self.sequ.get_activeProbeProfile()            
            if "flushTarget_H2O" in currentProbeProfile.keys() and self.sequ.picarroInfo["H2O"] <= currentProbeProfile["flushTarget_H2O"]: textCol = "#fff"
            if "H2O_Alert" in self.sequ.conf.keys() and self.sequ.picarroInfo["H2O"] >= self.sequ.conf["H2O_Alert"]: textCol = "#f80"            
                
            self.extraLabel.configure(text=u"H\u2082O: " + "%5.0f [ppmV]"%self.sequ.picarroInfo["H2O"],
                                      bg = activeCol, fg = textCol)

        else:
            self.extraLabel.configure(text=u"H\u2082O:     no data      ", bg="#ddd", fg="#444")
        #----


        if self._job is not None:
            self.master.after_cancel(self._job)
            self._job = None
        self._job = self.after(500, self.update)
            

    def reset_progressBars(self):
        profile = self.sequ.get_activeProbeProfile()

        w = self.master.winfo_width()
        r = profile["flush"]["duration"]/(profile["flush"]["duration"]+profile["measure"]["duration"])
        for flowMode, length in [("flush", w*r),("measure",w*(1-r))]:                
            maxDuration = profile[flowMode]["duration"]
            self.progBars[flowMode]["bar"].configure(value=0, max=maxDuration, length=length)
            self.progBars[flowMode]["label"].configure(text = "%.0f/%.0f"%(0,maxDuration))      
        

    def update_progressBars(self):

        profile = self.sequ.get_activeProbeProfile()
         
        fDuration = profile["flush"]["duration"]
        mDuration = profile["measure"]["duration"]

        w = self.master.winfo_width()
        r = fDuration/(fDuration+mDuration)           
        for flowMode, length in [("flush", w*r),("measure",w*(1-r))]:

            if flowMode == self.sequ.activeProbe.mode:
                duration = duration = self.sequ.get_duration()
                maxDuration = profile[flowMode]["duration"]
                self.progBars[flowMode]["bar"].configure(value=duration, max=maxDuration, length=length)
                self.progBars[flowMode]["label"].configure(text = "%.0f/%.0f"%(duration,maxDuration))

if __name__ == "__main__":    
   
    import SerialDevices
    dInfo = SerialDevices.find_device("IsWISaS_Controller", [9600], cachePath = "../temp/serial.cch")   
    try:
        d = SerialDevices.IsWISaS_Controller(dInfo["port"], dInfo["baudRate"])
    except:
        d = SerialDevices.IsWISaS_Controller("foobar", 0)    

    sequencer = Sequencer.ProbeSequencer(confFile = "../config/valve.cfg", controller = d)

    root = tk.Tk()
    root.title("GUI_ValveControl")
    root.geometry("%dx%d+%d+%d"%(250,800,1,0))    
    g = ValveControlFrame(root, sequencer, relief=tk.RAISED)
    g.pack(fill=tk.BOTH, expand=1)
    root.mainloop()
