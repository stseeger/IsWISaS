
#---- ToolTip was found in on the internet -------------

""" tk_ToolTip_class101.py
gives a Tkinter widget a tooltip as the mouse is above the widget
tested with Python27 and Python34  by  vegaseat  09sep2014
www.daniweb.com/programming/software-development/code/484591/a-tooltip-class-for-tkinter

Modified to include a delay time by Victor Zaccardo, 25mar16
"""

try:
    # for Python2
    import Tkinter as tk
except ImportError:
    # for Python3
    import tkinter as tk

class ToolTip(object):
    """
    create a tooltip for a given widget
    """
    def __init__(self, widget, text='widget info'):
        self.waittime = 500     #miliseconds
        self.wraplength = 200   #pixels
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)        
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):   
        x = self.widget.winfo_pointerx()+15
        y = self.widget.winfo_pointery()+10     
    
        # creates a toplevel window
        self.tw = tk.Toplevel(self.widget)       
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(self.tw, text=self.text, justify='left',
                       background="#ffffff", relief='solid', borderwidth=1,
                       wraplength = self.wraplength)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()

#---- ListboxLabel created by Stefan Seeger -------------
class ListboxLabel(tk.Label):
    def __init__(self, master, itemList, activeIndex = 0, listWidth=None, bg=None, listHeight=5, *args, **kwargs):
        super(ListboxLabel,self).__init__(master, *args, **kwargs)

        if bg is None: bg = "#fff"
        if listWidth is None: listWidth = max([len(x) for x in itemList])+5
        if listHeight is None: listHeight = len(itemList)
        self.itemList = itemList
        self.activeIndex = activeIndex
        self.activeLabel = itemList[activeIndex]
        
        self.configure(text=itemList[activeIndex], bg=bg)

        self.listbox = tk.Listbox(self.master, width = listWidth, height = listHeight+1)
        self.listbox.insert("end", *itemList)

        self.bind("<Button-1>", self.show_listbox)
        self.listbox.bind("<Leave>", self.on_listboxLeave)
        self.listbox.bind("<ButtonRelease-1>", self.on_listboxClick)
        self.listbox.bind("<KeyRelease-Return>", self.on_listboxClick)
     

    def show_listbox(self,event):        
        w0 = self.winfo_width()
        w1 = self.listbox.winfo_width()
        self.listbox.place(x=self.winfo_x() + (w0-w1)/2, y=self.winfo_y())
        self.listbox.lift()

    def on_listboxLeave(self, event):
        self.listbox.place_forget()

    def on_listboxClick(self, event):
         n = self.listbox.curselection()[0]
         self.activeIndex = n
         self.activeLabel = self.itemList[n]
         self.configure(text=self.itemList[n])
         self.listbox.place_forget()

    def set_activeLabel(self, newLabelText):
        self.configure(text=newLabelText)
        self.activeLabel = newLabelText
        try:
           self.activeIndex  = self.itemList.index(newLabelText)
        except:
            self.activeIndex = None
        


# testing ...
if __name__ == '__main__':
    root = tk.Tk()
    root.title("Extra widget test")

    t = ListboxLabel(root, itemList = ["Click","foo","bar"])
    t.grid(row=0, column=0,sticky='we')

    u = ListboxLabel(root, itemList = ["here","foo","bar"])
    u.grid(row=1, column=0,sticky='we')
    
    btn1 = tk.Button(root, text="Hover here to see tool tip 1")
    btn1.grid(row=0,column=1)
    button1_ttp = ToolTip(btn1, 'This is tool tip 1')

    btn2 = tk.Button(root, text="Hover here to see tool tip 2")
    btn2.grid(row=1,column=1)
    button2_ttp = ToolTip(btn2, 'This is tool tip 2')


    tk.Button(root, text="dummy 1").grid()
    tk.Button(root, text="dummy 2").grid()
    tk.Button(root, text="dummy 3").grid()
    tk.Button(root, text="dummy 4").grid()
    
    root.mainloop()
