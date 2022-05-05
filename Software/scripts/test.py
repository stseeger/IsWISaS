import tkinter as tk

tileWidth = 37
tileHeight = 20
tileMargin = 4
tileColumns = 4

baseAreaWidth = tileColumns*(tileWidth+tileMargin)

class BaseItem():
    def __init__(self, canvas, name, position, active=True):
        self.cv = canvas
        self.name = name
        self.active = active
        self.position = position

        x0, y0, x1, y1 = self.coords_from_position()        

        box=canvas.create_rectangle(self.coords_from_position(),
                                    outline="white", fill="grey", tags=("box", name))       

        label=canvas.create_text(x0,y0, text=name, fill="white", tags=("label", name), anchor="nw", font=('Helvetica','10'))
        self.position_label(box,label)

        self.boxId = box
        self.labelId = label

        self.bind_events()

    def coords_from_position(self, position = None):

        if position is None:
            position = self.position

        col = position % tileColumns
        row = position // tileColumns        
        
        y0 = row * (tileHeight + 2*tileMargin)
        x0 = col * (tileWidth + tileMargin)
        
        return x0, y0, x0+tileWidth, 5+ y0 + tileHeight  

    def position_label(self, boxId, labelId):   

        box = self.cv.coords(boxId)

        boxW = box[2]-box[0]
        boxH = box[3]-box[1]

        fontSize = round((boxH-8)/1.5)
        
        self.cv.itemconfig(labelId, font = ("Helvetica", "%d"%fontSize))
        label = self.cv.bbox(labelId)
        labelW =label[2]-label[0]

        while (labelW+8) > boxW:
            fontSize = fontSize - 1
            self.cv.itemconfig(labelId, font = ("Helvetica", "%d"%fontSize))
            label = self.cv.bbox(labelId)
            labelW =label[2]-label[0]

        labelH =label[3]-label[1]
            
        new = [round(box[0] + (boxW - labelW)/2) , round(box[1] + (boxH - labelH)/2)]

        self.cv.move(labelId,new[0]-label[0],new[1]-label[1])

    def get_itemList(self):
        allIds = list(self.cv.find_withtag("box"))
        positions = []
        items = []

        for id in allIds:
            item = self.cv.itemcget(id,'tags').replace(" current","").\
                   replace("label ","").replace("box ","")

            coords = self.cv.coords(id)
            positions.append(5*coords[1] + coords[0])
            items.append(item)

        return [x for y, x in sorted(zip(positions, items))]

    def mouse_releaseRight(self):
        print("right: "+self.name)
        

    def mouse_button1(self, mouse,object):
        self.cv.drag_drop_flag = True
        self.cv.tag_raise(object,None)

        self.cv.mousePos =[mouse.x, mouse.y]
        self.cv.startPos_dragDrop = [mouse.x, mouse.y]
        self.cv.initial_itemList = self.get_itemList()

    def mouse_releaseLeft(self):
        self.cv.drag_drop_flag = False

        if self.cv.mousePos[0] == self.cv.startPos_dragDrop[0] \
           and self.cv.mousePos[1] == self.cv.startPos_dragDrop[1]:
            print("left: "+self.name)

        if self.cv.mousePos[0] > baseAreaWidth:
            itemList = self.cv.initial_itemList
        else:
            itemList = self.get_itemList()
            

        for i,item in enumerate(itemList):
            ids = list(self.cv.find_withtag(item))
            ids.sort()
            
            box = ids[0]
            old = self.cv.coords(box)
            new = self.coords_from_position(i)
            self.cv.move(box,new[0]-old[0],new[1]-old[1])
            
            label = ids[1]
            self.position_label(box, label)
            self.cv.lift(label)

    def mouse_move(self, mouse,object):
        if self.cv.drag_drop_flag == True:
            
            xoff = mouse.x - self.cv.mousePos[0]
            yoff = mouse.y - self.cv.mousePos[1]
            
            tag = self.cv.itemcget(object,'tags').replace(" current","").\
                  replace("label ","").replace("box ","")

            allIds = list(self.cv.find_withtag(tag))

            for id in allIds:
                self.cv.move(id,xoff,yoff)
                if id == max(allIds):
                    self.cv.lift(id)

            self.cv.mousePos =[mouse.x, mouse.y]            

    def mouse_enter(self, event):
        self.cv.temp_cursor = self.cv['cursor']
        self.cv['cursor'] = 'hand2'

    def mouse_leave(self, event):
        cv['cursor'] = cv.temp_cursor
    

    def bind_events(self):

        for object in [self.boxId, self.labelId]:
            self.cv.tag_bind(object,"<Button-1>",        lambda e,obj=object:self.mouse_button1(e,obj))
            self.cv.tag_bind(object,"<ButtonRelease 1>", lambda e,obj=object:self.mouse_releaseLeft())
            self.cv.tag_bind(object,"<ButtonRelease 3>", lambda e,obj=object:self.mouse_releaseRight())
           
            self.cv.tag_bind(object,"<Motion>", lambda e,obj=object:self.mouse_move(e,obj))
            
            self.cv.tag_bind(object,"<Enter>", lambda e:self.mouse_enter(e))
            self.cv.tag_bind(object,"<Leave>", lambda e:self.mouse_leave(e))      
        

#class SequenceItem(BaseItem):
 #   def __init__(self, sequencFrrame, baseItem, active=True):
  #      super(SequenceItem,self).__init__(self, sequenceFrame, active)
   #     self.baseItem = baseItem

      

#*** MODUL-TEST: CANVAS-OBJECT-MOVE WITH MOUSE ***
if __name__ == '__main__':

    root = tk.Tk()
    root.title("Drag&Drop Canvas-Object-Move")

    #~~ Erzeugt Canvasfläche für die Aufnahme von Canvas-Objekten
    cv = tk.Canvas(root,height=450,width=450,bd=0,relief='raised',bg='khaki2')
    cv.create_rectangle(0,0,tileColumns*(tileWidth+tileMargin),450)
    cv.pack()

    #~~ Folgende Variablen werden dem cv.objekt angehängt
    cv.drag_drop_flag = False
    cv.mouse_x = None
    cv.mouse_y = None

    baseItems = []
    for p in ["A","B","C","D"]:
        for t in ["s", "t"]:
            for n in ["1","2","3","4"]:
                baseItems.append(p+t+n)

    for i,item in enumerate(baseItems):
        BaseItem(cv, item, i)    
    
    root.mainloop()
