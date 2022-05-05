import datetime
import time
import os

weekdaysShort = ["Mon","Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
weekdaysLong = ["Monday","Tuesday", "Wednsday", "Thursday", "Friday", "Saturday", "Sunday"]

class Task():
    def __init__(self, timeString, valve, tolerance = 0):

        self.valve = valve.strip()
        self.tolerance = tolerance
        self.weekday = None
        
        timeString = timeString.strip().split(' ')
        
        if len(timeString)>1:
            dayString = timeString[0].strip()
            try:
                self.weekday = weekdaysShort.index(dayString)
            except:
                try:
                    self.weekday = weekdaysLong.index(dayString)
                except:
                    print("failed to interpret %s as weekday :("%dayString)
                    
                                    
        timeString = timeString[-1]                
        
        timeString = timeString.split(':')
        self.hour = float(timeString[0])
        self.minute = float(timeString[1])

    def timeTillNext(self):
        now = datetime.datetime.now()

        if self.weekday is None:
            d = 0
        else:
            d = self.weekday - now.weekday()
        
        h = self.hour - now.hour
        m = self.minute - now.minute
        t = d*24+h+m/60

        if t<0:
            if self.weekday is None:
                t+=24
            else:
                t+=168

        x = t
        if x > 24:
            d = int(x/24)
            x = x-d*24
        else:
            d = 0

        if x > 1:
            h = int(x)
            x = x-h
        else:
            h=0

        m = round(x*60)


        if d > 0:
            timeString = "%dd %02dh"%(d, h)
        elif h > 0:
            timeString = "%02dh %02dm"%(h, m)
        elif m > 0:
            timeString = "%02dm"%m
        else:
            timeString = "now"

        return [t, timeString, self.weekday is None]
                

class Scheduler():
    def __init__(self, configFile = "../config/schedule.conf"):
        self.tasks = {}

        if not os.path.isfile(configFile):
            print("No schedule file found...") 
            return

        print("Load schedule from %s"%configFile) 
        f = open(configFile, 'r')
        for line in f:
            if line.startswith('#'): continue
            splitLine = line.replace('\n','').split(';')
            self.tasks[splitLine[0].strip()] = Task(splitLine[0],splitLine[1])

        print("Events scheduled for:", list(self.tasks.keys())) 

        self.update()

    def update(self):

        if not len(self.tasks):
            return None

        valves = []
        timeLeft = []
        timeString = []
        daily = []
        
        for key in self.tasks.keys():
            valves.append(self.tasks[key].valve)
            r = self.tasks[key].timeTillNext()
            timeLeft.append(r[0])
            timeString.append("%s\n%s"%(self.tasks[key].valve,r[1]))
            daily.append(r[2])

        i = timeLeft.index(min(timeLeft))       

        return {"timeLeft": timeLeft[i], "label": timeString[i], "valve": valves[i]}
            
        #now = datetime.datetime.now().timestamp()
        #minTime = float("inf")
        #valve = None        

        #for key in self.tasks.keys():
        #    task = self.tasks[key]
        #    remainingTime = task.interval-((now-task.basetime)%task.interval)
        #    if remainingTime < minTime:
        #        minTime = remainingTime
        #        valve = task.valve

        #self.next = {"valve": valve, "timeLeft": minTime}
        #return self.next


s = Scheduler()
print(s.update())

