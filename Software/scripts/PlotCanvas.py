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
    def __init__(self,master, plotRangeX, plotRangeY, marginX=62, marginY=20, axes=True, selectionHandler = None, objectClickHandler=None, YPrecision=1, *args,**kwargs):
        super(PlotCanvas,self).__init__(master=master,*args,**kwargs)

        self.pxWidth = int(self.cget("width"))
        self.pxHeight = int(self.cget("height"))

        self.marginX = marginX
        self.marginY = marginY

        self.plotRangeX = plotRangeX
        self.plotRangeY = plotRangeY
        self.precisionY = YPrecision

        self.selectionHandler = selectionHandler
        self.objectClickHandler = objectClickHandler

        self.selection = {"left":[None,None], "right":[None,None]}
        self.lastMouseButton = None

        self.bind("<Button-1>", self.on_click)
        self.bind("<ButtonRelease-1>", self.on_click_release)
        self.bind("<B1-Motion>",self.on_drag)
        
        self.bind("<Button-3>",self.on_click)
        self.bind("<ButtonRelease-3>",self.on_click_release)
        self.bind("<B3-Motion>",self.on_drag)

        self.tag_bind("clickable", "<1>", self.objectClick)

        if str(type(axes)) == "<class 'bool'>": axes = [axes]
        if len(axes)==1: axes.extend(axes)
        if(axes[0]): self.draw_xAxis()
        if(axes[1]): self.draw_yAxis()

        self.buttonSpecs = [{"button":"right", "color":"#0af"}, {"button":"left", "color":"#fa0"}]

    #---------selection-------
    def objectClick(self, event):
        #self.selectionHandler=None

        item = self.find_closest(event.x, event.y)
        tags = self.itemcget(item, "tags").split(' ')

        ID=None
        time=None
        for tag in tags:            
            if tag.startswith("ID:"):
                ID= tag.split("ID:")[1]                
            if tag.startswith("time:"):
                time= tag.split("time:")[1]
            if ID and time:
                break

        if time is None:
            time = "all"

        if ID is None:
            ID = "none"

        if self.objectClickHandler is None:
            print(ID +':'+ time)
        else:
            self.objectClickHandler(ID, time)
        

        
    def get_buttonSpecs(self, event):        
        if event.num == "??":
            button = self.lastMouseButton
        else:
            button = event.num
            
        return self.buttonSpecs[button==1]
        
    def on_click_release(self, event):

        if self.selectionHandler is None:
            return
        
        specs = self.get_buttonSpecs(event)
        
        self.delete("selectStart_%s"%specs["button"])
        self.delete("dragEnd_%s"%specs["button"])
        
        self.selection[specs["button"]][1] = self.get_time(event)
        self.selectionHandler(self.selection[specs["button"]], button=specs["button"])       

    def on_click(self, event):
        if self.selectionHandler is None:
            return
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
        

    def draw_xAxis(self, plotRangeX = None, optimalTicks = 10, timeFormat = "%H:%M:%S", precision=None):
        self.delete("xAxis")

        if not plotRangeX is None:
            self.plotRangeX = plotRangeX
        
        firstTickOffset, spacing, tickCount = self.compute_optimalTicks(self.plotRangeX, optimalTicks, possibleTimeSpacings)
        
        self.xAxis = self.create_line(self.marginX,self.pxHeight-self.marginY, self.pxWidth, self.pxHeight-self.marginY, tags="xAxis")
        for i in range(tickCount+1):
            if i==0 and (firstTickOffset/spacing) > 0.15:
                continue

            x = self.marginX + (spacing*i-firstTickOffset) * self.xFactor()
            if timeFormat is None:
                timeLabel = self.plotRangeX[0]+(spacing*i-firstTickOffset)
            else:
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
                self.create_text(x+2, y[1], text = labels[i], tags=tag, fill=color[i], anchor = labelAnchor)

    def plotData(self, x, y, tag="data1", color="black", width=1, labelXoffset=0, plotLumpSize = 1):

        if plotLumpSize > 1 and len(x) > 100:
            x = x[0::int(plotLumpSize)]
            y = y[0::int(plotLumpSize)]
        
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

    def plotLine(self, x0, y0, x1, y1, tag="line"):
        self.delete(tag)
        self.create_line(self.getX(x0),self.getY(y0),self.getX(x1),self.getY(y1), width=1, tag=tag)
        

    def plotPoints(self, x, y, col, labels=None, labelOffsets=[0,0], idTag=None, timestamp=None, tag="points", size=5, lwd=1, borderCol="#000000"):
        self.delete(tag)

        if not isinstance(col, list):
            col = [col for i in range(len(x))]

        if not isinstance(borderCol, list):
            borderCol = [borderCol for i in range(len(x))]

        if not isinstance(size, list):
            size = [size for i in range(len(x))]

        if not isinstance(lwd, list):
            lwd = [lwd for i in range(len(x))]

        if idTag is None:
            idTag = labels

        for i in range(len(x)):
            tags = [tag, "clickable"]
            if not idTag is None:
                tags = tags + ["ID:"+idTag[i]]
            if not timestamp is None:
                tags = tags + ["time:%.0f"%timestamp[i]]
            
            self.create_rectangle(self.getX(x[i])-size[i], self.getY(y[i])-size[i],
                                  self.getX(x[i])+size[i], self.getY(y[i])+size[i],
                                  fill=col[i], tags=tags, width=lwd[i], outline=borderCol[i])

            if not labels is None:                
                tags = tags + ["ID:"+labels[i]]
                self.create_text(self.getX(x[i])+labelOffsets[0],
                                 self.getY(y[i])+labelOffsets[1], text=labels[i], tags=tags, anchor='w')

    def on_resize(self, width, height):
        self.pxWidth = width
        self.pxHeight= height
        self.config(width=self.pxWidth, height=self.pxHeight)

#===========================================
            
        
