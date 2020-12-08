import tkinter as tk
import time
import colorsys

#---- possible tick spacings ----
possibleTickSpacings = []
for y in range(-4,7):
    for x in [1,2,5]:
        possibleTickSpacings.append(float("%de%d"%(x,y)))


possibleTimeSpacings = [1, 10, 30, 60, 120, 300, 600, 900, 1800, 3600, 7200, 21600, 86400, 172800, 432000, 2592000, 15552000]

class PlotCanvas(tk.Canvas):
    def __init__(self,master, plotRangeX, plotRangeY, marginX=62, marginY=20, axes=True, selectionHandler = None, *args,**kwargs):
        super(PlotCanvas,self).__init__(master=master,*args,**kwargs)

        self.pxWidth = int(self.cget("width"))
        self.pxHeight = int(self.cget("height"))

        self.marginX = marginX
        self.marginY = marginY

        self.plotRangeX = plotRangeX
        self.plotRangeY = plotRangeY
        self.precisionY = 1

        self.selectionHandler = selectionHandler

        self.selection = {"left":[None,None], "right":[None,None]}
        self.lastMouseButton = None

        self.bind("<Button-1>", self.on_click)
        self.bind("<ButtonRelease-1>", self.on_click_release)
        self.bind("<B1-Motion>",self.on_drag)
        
        self.bind("<Button-3>",self.on_click)
        self.bind("<ButtonRelease-3>",self.on_click_release)
        self.bind("<B3-Motion>",self.on_drag)

        if str(type(axes)) == "<class 'bool'>": axes = [axes]
        if len(axes)==1: axes.extend(axes)
        if(axes[0]): self.draw_xAxis()
        if(axes[1]): self.draw_yAxis()

        self.buttonSpecs = [{"button":"right", "color":"#0af"}, {"button":"left", "color":"#fa0"}]

    #---------selection-------
    def get_buttonSpecs(self, event):        
        if event.num == "??":
            button = self.lastMouseButton
        else:
            button = event.num
            
        return self.buttonSpecs[button==1]
        
    def on_click_release(self, event):
        specs = self.get_buttonSpecs(event)
        
        self.delete("selectStart_%s"%specs["button"])
        self.delete("dragEnd_%s"%specs["button"])
        
        self.selection[specs["button"]][1] = self.get_time(event)
        self.selectionHandler(self.selection[specs["button"]], button=specs["button"])       

    def on_click(self, event):
        specs = self.get_buttonSpecs(event)
        self.selection[specs["button"]][0] = self.get_time(event)
        self.vertLines([self.selection[specs["button"]][0]], tag="selectStart_%s"%specs["button"], width=3, color=specs["color"])
        self.lastMouseButton = event.num

    def on_drag(self, event):
        specs = self.get_buttonSpecs(event)
        self.selection[specs["button"]][1] = self.get_time(event)
        self.delete("dragEnd_%s"%specs["button"])
        self.vertLines([self.selection[specs["button"]][1]], tag="dragEnd_%s"%specs["button"], width=3, color=specs["color"])

    def get_time(self, event):
        relTime = (event.x - self.marginX) / (self.pxWidth - self.marginX)
        return(self.plotRangeX[0] + (self.plotRangeX[1]-self.plotRangeX[0]) * relTime)        

    def yFactor(self):
        plotHeight = self.plotRangeY[1] - self.plotRangeY[0]
        if plotHeight:
            return((self.pxHeight-self.marginY-10) / (self.plotRangeY[1]-self.plotRangeY[0]))
        return 1

    def xFactor(self):
        plotWidth = self.plotRangeX[1]-self.plotRangeX[0]
        if plotWidth:
            return((self.pxWidth-self.marginX) / plotWidth)
        return 1


    def compute_optimalTicks(self, values, optimalTickCount = 10, possibleSpacings = possibleTickSpacings):
        valDiff = values[-1]-values[0]        
        neededTicks = [abs(round(valDiff/s)) for s in possibleSpacings]
        deviation = [abs(n - optimalTickCount) for n in neededTicks]
        bestIndex = deviation.index(min(deviation))
        spacing = possibleSpacings[bestIndex]
        firstTickOffset = values[0] -(round(values[0]/spacing)*spacing)

        return firstTickOffset, possibleSpacings[bestIndex], neededTicks[bestIndex]

    def draw_yAxis(self, plotRangeY = None, precision=None, optimalTicks = 5):

        self.delete("yAxis")

        if precision is None:
            precision = self.precisionY
        else:
            self.precisionY = precision
            

        if not plotRangeY is None:
            self.plotRangeY = plotRangeY
        
        firstTickOffset, spacing, tickCount = self.compute_optimalTicks(self.plotRangeY, optimalTicks)

        self.yAxis = self.create_line(self.marginX,self.pxHeight-self.marginY, self.marginX, 0, tags="yAxis")
        
        for i in range(tickCount+1):
            if i==0 and (firstTickOffset/spacing) > 0.15:
                continue

            y = self.pxHeight-self.marginY - (spacing*(i)-firstTickOffset) * self.yFactor()
            self.create_line(self.marginX-5, y, self.marginX, y, tags=["yAxis","tickMark"])
            self.create_text(self.marginX-32, y, text=('%0.*f' %(precision, self.plotRangeY[0]+(spacing*i-firstTickOffset))), tags=["yAxis","tickLabel"])
        

    def draw_xAxis(self, plotRangeX = None, optimalTicks = 10, timeFormat = "%H:%M:%S"):
        self.delete("xAxis")

        if not plotRangeX is None:
            self.plotRangeX = plotRangeX
        
        firstTickOffset, spacing, tickCount = self.compute_optimalTicks(self.plotRangeX, optimalTicks, possibleTimeSpacings)
        
        self.xAxis = self.create_line(self.marginX,self.pxHeight-self.marginY, self.pxWidth, self.pxHeight-self.marginY, tags="xAxis")
        for i in range(tickCount+1):
            if i==0 and (firstTickOffset/spacing) > 0.15:
                continue

            x = self.marginX + (spacing*i-firstTickOffset) * self.xFactor()
            timeLabel =  time.strftime(timeFormat, time.gmtime(self.plotRangeX[0]+(spacing*i-firstTickOffset)))            
            self.create_line(x, self.pxHeight-self.marginY+5, x, self.pxHeight-self.marginY, tags=["xAxis","tickMark"])
            self.create_text(x, self.pxHeight-self.marginY+12, text=timeLabel, tags=["xAxis","tickLabel"])
        

    def getX(self,value):
        value = value-self.plotRangeX[0]
        return(int(self.marginX + self.xFactor()*value))

    def getY(self,value):
        value = value-self.plotRangeY[0]
        return(int((self.pxHeight-self.marginY) - self.yFactor()*value))

    def getPixelCoordinates(self,tupleOfValuePairs):
        convertedValues=[]
        for i, value in enumerate(tupleOfValuePairs):
            if i%2:
                convertedValues.append(self.getY(value))
            else:
                convertedValues.append(self.getX(value))
        return(tuple(convertedValues))

    def set_xLab(self, xLab):
        self.xLab = xLab

    def set_yLab(self, yLab):
        self.yLab = yLab    

    def coords(self, tags, tupleOfValuePairs):
        tupleOfValuePairs = self.getPixelCoordinates(tupleOfValuePairs)
        super(PlotCanvas,self).coords(tags, tupleOfValuePairs)

    def vertBoxes(self, xValues1, xValues2, tag ="vertBoxes", color = "gray90", width=0):
        self.delete(tag)
        y = [self.getY(self.plotRangeY[0]), self.getY(self.plotRangeY[1])]
        if not str(type(color)) == "<class 'list'>":
            color = [color for n in range(len(xValues1))]

        for i,xValue1 in enumerate(xValues1):
            x1 = self.getX(xValue1)
            x2 = self.getX(xValues2[i])
            self.create_rectangle(x1, y[0], x2, y[1], tags=tag, fill = color[i], width=width)

    def relativeLabel(self, xValue, relYValue, labelText, tag="extraLabel", color = "#aaa"):
        self.delete(tag)
        if not type(xValue) == list:
            xValue = [xValue]
            relYValue = [relYValue]
            labelText = [labelText]

        for i in range(len(xValue)):
            y = self.getY(self.plotRangeY[0] + relYValue[i] * (self.plotRangeY[1] - self.plotRangeY[0]))
            x = self.getX(xValue[i])
            self.create_text(x, y, text = labelText[i], tags = tag, fill = color)

    def vertLines(self, xValues, labels=None, tag="vertLines", color="gray80", width=1, labelAnchor = tk.W, dash=None):
        self.delete(tag)
        y = [self.getY(self.plotRangeY[0]), self.getY(self.plotRangeY[1])]

        if not str(type(color)) == "<class 'list'>":
            color = [color for n in range(len(xValues))]            

        for i,xVal in enumerate(xValues):
            x = self.getX(xVal)
            self.create_line(x, y[0], x, y[1]-10, tags=tag, fill = color[i], width=width, dash = dash)
            if not labels is None:
                self.create_text(x, y[1], text = labels[i], tags=tag, fill=color[i], anchor = labelAnchor)

    def plotData(self, x, y, tag="data1", color="black", width=1, labelXoffset=0):
        
        self.draw_xAxis()
        self.draw_yAxis()

        self.delete("error")
        self.delete(tag)

        if len(x) < 2 | len(y) < 2:
            return()

        for i in range(2,len(x)):
            self.create_line(self.getX(x[i-1]), self.getY(y[i-1]), self.getX(x[i]), self.getY(y[i]), tags=tag, fill = color, width=width)

        if labelXoffset:
            self.create_text(self.getX(x[-1])-labelXoffset, self.getY(y[-1])-10,text = y[-1], fill = color, tags=tag)

    def on_resize(self,width,height):
        self.pxWidth = width
        self.pxHeight= height
        self.config(width=self.pxWidth, height=self.pxHeight)

#============================================

class LogFileOverviewCanvas(PlotCanvas):
    def __init__(self, master, startTimes, stopTimes, valveTimes = None, loadHandler=None, selectionHandler=None, *args,**kwargs):
        self.totalRange = [startTimes[0],stopTimes[-1]]
        plotRangeX = self.totalRange
        super(LogFileOverviewCanvas,self).__init__(master=master, plotRangeX = plotRangeX, plotRangeY=[0,4], marginX=0, marginY=15, axes=True, selectionHandler = selectionHandler, *args,**kwargs)
        self.startTimes = startTimes
        self.stopTimes = stopTimes
        self.valveTimes = valveTimes        
        self.loadHandler = loadHandler        
        self.lastClickY = 0
        self.periods = {}

        if selectionHandler is None:
            selectionHandler = self.change_selection
        self.selectionHandler = selectionHandler
        
        self.draw_overviewRects()
    
    def draw_overviewRects(self):        
        cols = ["#9f9","#7d7"]
        self.delete("overview")

        timeRange = self.plotRangeX[1]-self.plotRangeX[0]
        timeFormat = "%Y"
        if timeRange < 86400*365*2:
            timeFormat = "%Y-%m"
            if timeRange < 86400*365:
                timeFormat = "%Y-%m-%d"
                if timeRange < 86400 * 10:
                    timeFormat = "%d.%m. %H:%M"
        self.draw_xAxis(optimalTicks=10, timeFormat = timeFormat)

        if not self.valveTimes is None:
            y0 = self.getY(self.plotRangeY[1])-5
            y1 = y0+5
            for t in self.valveTimes:
                self.create_line(self.getX(t), y0, self.getX(t), y1, tags="overview", fill = "#008", width=2)
                    
        for n in range(len(self.startTimes)):           
            self.create_rectangle(self.getX(self.startTimes[n]),
                                  self.getY(self.plotRangeY[0]),
                                  self.getX(self.stopTimes[n]),
                                  self.getY(self.plotRangeY[1]),
                                  tags="overview", fill=cols[n%2], width=0)

        #widths = [x["width"] for x in self.periods.values()]
        for periodName in self.periods.keys():           
            self.delete(periodName)
            if self.periods[periodName]["period"] is None: continue
            self.vertLines(self.periods[periodName]["period"], tag=periodName,
                           width=self.periods[periodName]["width"],
                           color=self.periods[periodName]["color"]) 

    def set_period(self, period, name, linecolor, linewidth=2):        
        self.periods[name] = {"period": period, "color": linecolor, "width": linewidth}        
        self.delete(name)
        self.vertLines(period, tag=name, color=linecolor, width= linewidth)        

    def change_selection(self, selection=None, button="left"):

        if button=="left":
        
            if selection is None:
                selection = [self.startTimes[0], self.stopTimes[-1]]               

            selection.sort()

            intervalLength = selection[1] - selection[0]        
            if (intervalLength) < 28800:                
                m = (selection[0]+selection[1])/2
                selection = [m - 14400, m+ 14400]
                            
            self.plotRangeX = selection.copy()
            self.draw_overviewRects()

        else:
            self.loadHandler(selection)            

    def on_resize(self,width,height):
        super(LogFileOverviewCanvas,self).on_resize(width, height)
        self.draw_overviewRects()
        
            
            
        
