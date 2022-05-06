import tkinter as tk
from tkinter import ttk
from tkinter import font as tkFont
import time
import collections
import math

import configLoader
import const
import DataBuffer

def process_cfg(cfg):
    # make sure that a state is assigned (even if not specified in cfg file)
    for ID in cfg["ID"].keys():

        if not "group" in cfg["ID"][ID].keys():
            splitSlot = cfg["ID"][ID]["slot"].split('#')
            if len(splitSlot)>1:
                group = int(splitSlot[0])
            else:
                group = 1
            cfg["ID"][ID]["group"] = group
        
        if not "state" in cfg["ID"][ID].keys():
            cfg["ID"][ID]["state"] = 1

    # when no sequence is defined, take the sequence from the probe definition table
    if not "sequence" in cfg.keys():        
        cfg["sequence"] = list(cfg['ID'].keys())
    # otherwise, discard items from the sequence that are not defined in the probe definition table
    else:
        sequence = []
        for item in cfg["sequence"]:
            if item in cfg["ID"].keys():
                sequence.append(item)
            else:
                print("Sequence element '%s' is missing in ID-table and will be ignored"%item)
        cfg["sequence"] = sequence

    # check initialID and remove it if not valid
    if "initialID" in cfg.keys():
        if not cfg["initialID"] in cfg["ID"]:
            del cfg["initialID"]
        cfg["autostart"]=False
    else:
        cfg["autostart"]=True

    # determine initialID in case it is missing
    if not "initialID" in cfg.keys():
        for ID in cfg["sequence"]:
            if cfg["ID"][ID]["state"] > 0:                
                cfg["initialID"] = ID
                break


    for key in cfg["probeType"].keys():
        dataDict = {}

        for phase in ["flush", "measure"]:
            splitEntry = cfg["probeType"][key][phase] .split('@')

            # everything before the @ should be a time specification
            # without a given unit, s is the default
            try:
                number = float(splitEntry[0].replace("s",""))
            except:
                try:
                    number = 60 * float(splitEntry[0].replace("min",""))
                except:
                    try:
                        number = 3600 * float(splitEntry[0].replace("h",""))
                    except:
                        print("!!!could not interpret %s !!!"% splitEntry[0])
                        number = 60

            #everything after the @ is optional and should specify flow rates
            overwriteValve = None
            flowRateA=0
            flowRateB=0

            if len(splitEntry)>1:
                flowRates = splitEntry[1].split('+')
                try:
                    flowRateA = float(flowRates[0])
                except:
                    overwriteValve = flowRates[0]
                try:
                    flowRateB = float(flowRates[1])
                except:
                    flowRateB = 0            

            dataDict[phase] = {"duration":number, "flowA":flowRateA, "flowB":flowRateB,
                                "overwriteValve":overwriteValve}

        dataDict["postFlush"] = dataDict["flush"].copy()
        dataDict["flushTarget_H2O"] = cfg["probeType"][key]["flushTarget_H2O"]
            
        cfg["probeType"][key] = dataDict       

        
        
    return cfg

#--------------------
class SequenceItem():    
    def __init__(self, ID, enabled=True):
        self.ID = ID
        self._enabled = enabled

    def isActive(self):
        return self._enabled

    def toggle_activity(self, enabled=None):
        if enabled is None:
            self._enabled = not self._enabled
        else:
            self._enabled = enabled

#--------------------
class Probe(SequenceItem):

    FLUSH = "flush"
    MEASURE = "measure"
    POSTFLUSH = "postFlush"
    
    def __init__(self, ID, slot, group, probeType, enabled=True):

        super(Probe,self).__init__(ID, enabled)

        try:
            splitSlot = slot.split('#')
            self.box  = int(splitSlot[0])
            self.slot = int(splitSlot[1])
        except:
            self.box  = 0
            self.slot =int(slot)

        self.group = group
        self.type = probeType
        
        self.mode = self.FLUSH
        self.lastToggleTime = time.time()

    def __repr__(self):
        return("<\"%s\"(%s)>"%(self.ID, self.type))

        
    def toggle_mode(self, newMode=None):
        if newMode is None:
            if self.mode==self.FLUSH:
                self.mode = self.MEASURE
            else:
                self.mode = self.FLUSH
        else:
            self.mode = newMode

        self.lastToggleTime = time.time()


#--------------------        
            

class ProbeSequencer():

    def __init__(self, confFile = "../config/valve.cfg", controller = None):

        self.confFile = confFile

        self.position = -1
        self.load_conf()

        self._enabled = True
        self.activeProbe = None

        self._alarmed = False
        self._dry = False
        self._stable = False
        self._flushing = False
        self.picarroInfo = None

        self.controller = controller

        # ----- prepare valve log file ----

        parActiveValve = DataBuffer.Parameter(name = "ID", unit = "active valve")
        parMeasurement = DataBuffer.Parameter(name = "measurement", unit = "state")
        parSwitchCode = DataBuffer.Parameter(name = "switchCode", unit = "%d = start | %d = manual | %d = timeout | %d = optimal | %d = alert"\
                                                                          %(const.SWITCH_START,
                                                                            const.SWITCH_MANUAL,
                                                                            const.SWITCH_TIMEOUT,
                                                                            const.SWITCH_OPTIMUM,
                                                                            const.SWITCH_ALERT))
        
        self.valveBuffer = DataBuffer.Buffer(100, self.conf["logFile"], parameters = [parActiveValve, parMeasurement, parSwitchCode])

        # ---------------------------------
        self.toggle(enabled=self.conf["autostart"])        
        self.switch_probe(self.conf["initialID"], switchCode=0)

    def load_conf(self):
        
        self.conf = process_cfg(configLoader.load_confDict(self.confFile))       

        IDTable = self.conf["ID"]
        sequence = self.conf["sequence"]        
        probeTypeTable = self.conf["probeType"]

        self.initialID = self.conf["initialID"]
        
        if self.position == -1:
            for i in range(len(sequence)):
                if self.initialID == sequence[i]:
                    self.position = i
                    break

        self.probeDict = collections.OrderedDict()
        for i, ID in enumerate(IDTable.keys()):
            if IDTable[ID]["probeType"] in probeTypeTable.keys():
                pass
                #probeType = IDTable[ID]["probeType"]
            else:
                print("Probe type '"+IDTable[ID]["probeType"]+"' of probe'"+ID+"' is not defined, falling back to 'default'")
                #probeType = "default"
            self.probeDict[ID] = Probe(ID = ID,
                                       slot = IDTable[ID]["slot"],
                                       group = IDTable[ID]["group"],
                                       probeType = IDTable[ID]["probeType"],                                       
                                       enabled = IDTable[ID]["state"]>0)

        self.sequence = []
        for i, ID in enumerate(sequence):
            self.sequence.append(SequenceItem(ID))
                            
        self.probeTypes = probeTypeTable
        

    def isActive(self):
        return self._enabled
        
    def toggle(self, enabled=None):

        if enabled is None:
            self._enabled = not self._enabled
        else:
            self._enabled = enabled

        if self._enabled:
            print("==== sequence started ====")
        else:
            print("==== sequence stopped ====")

    def get_duration(self):
        return time.time() - self.activeProbe.lastToggleTime

    def get_activeProbeProfile(self):
        try:
            return self.probeTypes[self.activeProbe.type]
        except:
            #print("Probe type '"+self.activeProbe.type+"' is not defined, falling back to 'default'")
            return self.probeTypes["default"]

    def get_actuallyActiveProbe(self):
        overwriteID = self.get_activeProbeProfile()[self.activeProbe.mode]["overwriteValve"]

        if overwriteID is None:
            return self.activeProbe

        return self.probeDict[overwriteID]
        

    def get_nextPosition(self):

        if self.position >= len(self.sequence):           
            self.position = len(self.sequence)-1

        afterCurrentPos = list(range(self.position+1, len(self.sequence)))
        beforeCurrentPos = list(range(0, self.position))

        for i in  (afterCurrentPos + beforeCurrentPos):
            if self.sequence[i].isActive() and self.probeDict[self.sequence[i].ID].isActive():                
                return i

        return self.position    

    def set_valve(self):
        return        

    def toggle_activeProbeMode(self, newMode=None, switchCode = const.SWITCH_TIMEOUT):
        self.activeProbe.toggle_mode(newMode)

        actuallyActiveProbe = self.get_actuallyActiveProbe()

        self.valveBuffer.add([actuallyActiveProbe.ID, {"flush":0, "measure":1, "postFlush":2}[self.activeProbe.mode], switchCode])
        groupValve = "0#%d"%(actuallyActiveProbe.group)
        valve = "%d#%d"%(actuallyActiveProbe.box, actuallyActiveProbe.slot)

        print(self.activeProbe)
        ID = self.activeProbe.ID
        print('\t',self.activeProbe.mode,'@',actuallyActiveProbe.ID)

        self.controller.set_valve(valve+" "+groupValve)        
        

    def switch_probe(self, newProbeID, switchCode):

        if self.activeProbe is None or newProbeID != self.activeProbe.ID:
            print("----------------------")
        
        self.activeProbe = self.probeDict[newProbeID]        

        if self.get_activeProbeProfile()["flush"]["duration"]:
            self.toggle_activeProbeMode(Probe.FLUSH, switchCode)
        else:
            self.toggle_activeProbeMode(Probe.MEASURE, switchCode)

        #overwriteID = self.get_activeProbeProfile()[self.activeProbe.mode]["overwriteValve"]
        #if overwriteID:
        #    print(self.activeProbe.mode, self.activeProbe, 'over', self.probeDict[overwriteID])

    def switch_sequence(self, newPosition, switchCode):
        self.position = newPosition
        newID = self.sequence[newPosition].ID
        self.switch_probe(newID, switchCode=switchCode)

    def deactivate_currentGroup(self):       
        print("Disabling all probes of group '%s'"%self.activeProbe.group)
        
        for key in self.probeDict.keys():
            probe = self.probeDict[key]
            if probe.group == self.activeProbe.group:
                print("\t"+probe.ID)
                probe.toggle_activity(False)

    # ---- basic checks -----

    def isFlushing(self):
        return self.isActive() and self._flushing        
    
    def flushTimeout(self):
        return self.get_duration() >= self.get_activeProbeProfile()["flush"]["duration"]

    def measureTimeout(self):
        return self.get_duration() >= self.get_activeProbeProfile()["measure"]["duration"]

    def postFlushTimeout(self):
        return self.get_duration() >= self.get_cooldownTime()
        
    def get_cooldownTime(self):
        return self.conf["ID"][self.activeProbe.ID]["distance"] * self.conf["autoSwitchCooldown"]/10    

    def isAlarmed(self):

        try:
            alarmed = self.picarroInfo["H2O"] > self.conf["H2O_Alert"]
        except:
            alarmed = False       
        
        return alarmed or self._alarmed

    def isDryEnough(self):        

        try:
            dry = self.get_activeProbeProfile()["flushTarget_H2O"] > self.picarroInfo["H2O"]
        except:
            dry = False

        return (dry or self._dry) and self.get_duration() >= self.get_cooldownTime()

    def isStableEnough(self):        

        try:
            stable = self.picarroInfo["stable"]
        except:
            stable = False

        return (stable or self._stable) and self.get_duration() >= self.get_cooldownTime()

    # ---- combine checks ------------------
    def threeStageCheck(self, mode, timeoutFun, optimumFun):
        if self.activeProbe.mode!=mode:
            return 0

        if timeoutFun():
            return const.SWITCH_TIMEOUT

        if optimumFun():
            return const.SWITCH_OPTIMUM

        return 0

    
    # ----------------------------

    def proceed(self, switchCode):

        if self.activeProbe.mode == Probe.FLUSH:
            if self.get_activeProbeProfile()["measure"]["duration"]:
                if not self.picarroInfo is None:
                    if self.picarroInfo["H2O"] <= self.get_activeProbeProfile()["flushTarget_H2O"] :
                        self.toggle_activeProbeMode(Probe.MEASURE, switchCode = switchCode)
                    else:
                        self.switch_sequence(self.get_nextPosition(), switchCode=switchCode)                        
                else:
                    self.toggle_activeProbeMode(Probe.MEASURE, switchCode = switchCode)
            else:
                self.switch_sequence(self.get_nextPosition(), switchCode=switchCode)
            return

        if self.activeProbe.mode==Probe.POSTFLUSH or\
           (self.activeProbe.mode == Probe.MEASURE and not self.conf["postFlushEnable"]):
            self.switch_sequence(self.get_nextPosition(), switchCode=switchCode)
            return

        self.toggle_activeProbeMode(Probe.POSTFLUSH, switchCode=switchCode)
            
    
    def update(self, skip=False):

        if not self.sequence[self.position].isActive():
            self.switch_sequence(self.get_nextPosition(), switchCode=switchCode)
            return        

        if self.isAlarmed():
            if self.activeProbe.type != "flush":
                print("!!!WETNESS_ALARM RAISED!!!")
                self.deactivate_currentGroup()                
                print("Commence system flush...")
                self.switch_probe(self.conf["flushID"], switchCode=const.SWITCH_ALERT)
                self._flushing = True                
            else:
                p=self.get_activeProbeProfile()                
                # try to find another flush probe to relieve the current flush probe
                if self.get_duration() > self.get_activeProbeProfile()["flush"]["duration"]:                   
                    for key in self.probeDict.keys():
                        probe = self.probeDict[key]
                        if probe.type == "flush" and probe.ID != self.activeProbe.ID and probe.isActive():
                            self.switch_probe(key, switchCode=const.SWITCH_ALERT)
                            break
                        
            return
        
        elif self.isFlushing():
            print("WETNESS_ALARM CLEARED, continue sequence...")
            self._flushing = False            
            self.switch_sequence(self.get_nextPosition(), switchCode=const.SWITCH_OPTIMUM)
            return
                
        # --- during regular flush phases ----

        flushCode = self.threeStageCheck(Probe.FLUSH, self.flushTimeout, self.isDryEnough)
        if flushCode:
            print("\t\t%s"%["timeout","dry"][flushCode-2])
            self.proceed(flushCode)
            return

        measureCode = self.threeStageCheck(Probe.MEASURE, self.measureTimeout, self.isStableEnough)
        if measureCode:
            print("\t\t%s"%["timeout","stable"][measureCode-2])
            self.proceed(measureCode)
            return

        postFlushCode = self.threeStageCheck(Probe.POSTFLUSH, self.postFlushTimeout, self.isDryEnough)
        if postFlushCode:
            print("\t\t%s"%["timeout","dry"][measureCode-2])
            self.proceed(measureCode)
            return

        if skip:
            print("\tSkipping to next...")
            self.switch_sequence(self.get_nextPosition(), switchCode=const.SWITCH_MANUAL)
            
            
if __name__ == "__main__":
    pass

    
