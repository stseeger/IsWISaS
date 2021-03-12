import os

class FlowState():
    def __init__(self, rate, duration, rate_unit = "mL/min", duration_unit = "s"):
        self.rate = rate
        self.duration = duration
        self.rate_unit = rate_unit
        self.duration_unit = duration_unit

    def copy(self):
        return(FlowState(self.rate, self.duration, self.rate_unit, self.duration_unit))

    def __repr__(self):
        return "<%d %s for %d %s>"%(self.rate, self.rate_unit,
                                               self.duration, self.duration_unit)

class FlowStateAB(FlowState):
    def __init__(self, rateA, rateB, duration, rate_unit = "mL/min", duration_unit = "s"):

        super(FlowStateAB, self).__init__(rateA, duration, rate_unit, duration_unit)
        self.rateA = rateA
        self.rateB = rateB

    def copy(self):
        return(FlowStateAB(self.rateA, self.rateB, self.duration))

    def __repr__(self):
        return "<%d & %d %s for %d %s>"%(self.rateA, self.rateB, self.rate_unit,
                                         self.duration, self.duration_unit)
        
class FlowPattern():
    def __init__(self, name, flush, measure):
        self.name = name
        self.flush = flush
        self.measure = measure

    def copy(self):
        return(FlowPattern(self.flush.copy(), self.measure.copy()))


    def __repr__(self):
        return "<FlowPattern: flush %s and measure %s>"%(str(self.flush), str(self.measure))

class Valve():
    def __init__(self, number, name, flowPattern):
        self.number = number
        self.name = name
        self.flow = flowPattern

    def __repr__(self):        
        flowPatternName = "undefined" if self.flow is None  else self.flow.name
        return "<Valve: %s (%s)>"%(self.name, flowPatternName)
#=================================

def combine(primaryPath, secondaryPath, keyList = []):


    try:
        primary = load_confDict(primaryPath)
        secondary = None
        
    except:
        print("   !",primaryPath, "not found !")
        primary = load_confDict(secondaryPath)
        secondary = primary
        secondaryParameters = list(secondary.keys())

    primaryParameters = list(primary.keys())
    combined = primary.copy()
    missingParameters = []

    for parameter in keyList:
        try:
            primaryParameters.index(parameter)
        except:
            try:
                if secondary is None:
                    secondary = load_confDict(secondaryPath)                    
                    secondaryParameters = list(secondary.keys())
                secondaryParameters.index(parameter)
                combined[parameter] = secondary[parameter]
            except:
                missingParameters.append(parameter)

    if len(missingParameters):        
        raise Exception(primaryPath, "and", secondaryPath, "lack the definition of", missingParameters)

    return combined
    

def load_confDict(path, numericEntries = True, enforceList = []):
    print("Load", path, "...")
    confDict = {}
    f = open(path, 'r', encoding="UTF-8")
    insideTable = False
    insideSubEntry = False
    currentSubEntryKey = ''

    for line in f:        
        # skip comment lines and empty lines
        if line.startswith('#') or line == '\n': continue
        if line.startswith('-'):
            insideTable = False
            continue

        # split lines into key (before first ':) and entry (after first ':')
        i = line.find(":")        
        splitLine = [line[:i], line[i+1:]]
        key = splitLine[0].strip()        

        # split entry along ';'
        if len(splitLine[1].split(";;"))>1:
            entry = [part.split(';') for part in splitLine[1].split(";;")]            
        else:
            entry = splitLine[1].split(';')

        for i,part in enumerate(entry):           
            if isinstance(part, list):
                for j, subPart in enumerate(part):
                    entry[i][j] = subPart.strip()
            else:                
                entry[i] = part.strip() # strip leading and trailing white spaces

            # if desired, try to convert to nuemric values
            if numericEntries:
                try:
                    entry[i] = float(part.strip())
                except:
                    pass

        # unlist lists of length 1, unless the key appears within "enforceList"
        if len(entry)==1 and key not in enforceList:
            entry = entry[0]        

        # every sequence of subsequent lines starting with '|' will be interpreted
        # as table, those parts need some special treatment
        if key.startswith('|'):
            if not insideTable:                
                tableDict = {}
                confDict[key[1:]] = tableDict
                subKeys = entry
                insideTable = True
            else:
                tableLine = {}
                tableDict[key[1:]] = tableLine
                for i,subKey in enumerate(subKeys):
                    tableLine[subKey] = entry[i]

        # normal treatment for single line entries
        elif len(key.split('|'))>1:            
            splitKey = key.split('|')            
            if not insideSubEntry or not (currentSubEntryKey == splitKey[0]):                
                subDict = {}
                confDict[splitKey[0]] = subDict
                insideSubEntry = True
                currentSubEntryKey = splitKey[0]
            subDict[splitKey[1].strip()] = entry
                
        else:
            insideTable = False
            insideSubentry = False
            confDict[key] = entry
            
    f.close()

    
    return(confDict)
    

def load_pathsCfg():    
    return(load_confDict("../config/paths.cfg"))

def load_fcCal():
    return(load_confDict("../config/fc.cal"))

def load_flowCfg(path = "../config/flow.cfg"):    
    flowDict = load_confDict(path)
    for key in flowDict.keys():
        entry = flowDict[key]
        flowDict[key] = FlowPattern(name = key,
                                    flush = FlowStateAB(rateA = entry[0], rateB=entry[1], duration = entry[2]),
                                    measure = FlowStateAB(rateA = entry[3], rateB=entry[4], duration = entry[5]))       
    return(flowDict)


def load_valveCfg(path = "../config/valve.cfg", flowDict=None):
    rawValveDict = load_confDict(path)

    valveSequence = list(map(lambda x: int(x), rawValveDict["valveSequence"]))

    valveDict = {}

    for key in rawValveDict["valve"].keys():
        valveInfo = rawValveDict["valve"][key]
        #print(valveInfo)

        if flowDict is None:
            flowPattern = None
        else:
            flowPattern = flowDict[valveInfo["flowProfile"]]

        valveDict[int(key)] = Valve(number = int(key), name = valveInfo["name"], flowPattern = flowPattern)
    
    
    if len(valveSequence):
        print("\tsequence:%s"%';'.join(map(lambda x: str(x),valveSequence)))
    else:
        print("no valve sequence defined")
    
    return (valveDict, rawValveDict["valveSequence"])

def load_logCfg(path="../config/log.cfg"):
    logCfg = load_confDict(path)
    return logCfg
    

def load_logConf(path="../config/log.cfg"):
    conf = {}
    f = open(path, 'r')
    for line in f:
        if line.startswith('#'): continue        
        splitLine = line.split(':')       
        if len(splitLine)==2:
            metaKey=splitLine[0].strip()
            splitLine = splitLine[1:]
        else:                        
            metaKey = None
        splitLine = splitLine[0].split('=')
        if len(splitLine)!=2: continue
        key = splitLine[0].strip()
        # split the line at ";", then split the parts by ',', finally strip white spaces
        entry = list(map(lambda sList: [s.strip() for s in sList],
                         map(lambda linepart: linepart.split(';'),
                             splitLine[1].split(';;'))))
        if metaKey is None:
            conf[key] = entry[0]
        else:
            if metaKey not in conf.keys():
                conf[metaKey] = {}
            conf[metaKey][key] = entry
                
    outCols = []

    for entry in conf["output_columns"]:
        x = list(map(lambda x: x.strip(),entry.split('>')))
        if len(x)==2:
            outCols.append(x)
    conf["output_columns"] = outCols
    
    return(conf)

if __name__ == "__main__":
    #x = load_confDict("../config/logDescriptors/picarroLxxxx-i.lgd")
       
    x = load_confDict("../config/default/logEntries.cfg")
    #log = load_logConf()
    
    #flow  = load_flowCfg("../config/flow.cfg") 
    #valve = load_valveCfg("../config/valve.cfg", flow)

    #x = load_confDict("../config/log.cfg")
    #x = load_logCfg()

    
