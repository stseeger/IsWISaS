import tkinter as tk
from tkinter import ttk
from tkinter import font as tkFont
import collections

import configLoader

class SequencerItem():
    def __init__(self, name, singular=False):
        self.name = name
        self.singular = singular

    def __str__(self):
        return self.name

class SequencerFrame(tk.Frame):
    def __init__(self, master, sequenceFile = "../config/sequence.cfg", *args, **kwargs):
        super(SequencerFrame,self).__init__(master, *args, **kwargs)
        self.master = master

        self.conf = configLoader.load_confDict(sequenceFile)

        self.sequence = list()
        for item in self.conf["sequence"]:
            if item in self.conf.keys():
                for subItem in self.conf[item]:
                    self.sequence.append(SequencerItem(subItem))
            else:
                self.sequence.append(SequencerItem(item))
        self.sequence.append(None)

        while len(self.sequence):
            print(self.sequence.pop(0))

class Drag_and_Drop_Listbox(tk.Listbox):
  """ A tk listbox with drag'n'drop reordering of entries. """
  def __init__(self, master, **kw):
    kw['selectmode'] = tk.MULTIPLE
    kw['activestyle'] = 'none'
    tk.Listbox.__init__(self, master, kw)
    self.bind('<Button-1>', self.getState, add='+')
    self.bind('<Button-1>', self.setCurrent, add='+')
    self.bind('<B1-Motion>', self.shiftSelection)
    self.curIndex = None
    self.curState = None
  def setCurrent(self, event):
    ''' gets the current index of the clicked item in the listbox '''
    self.curIndex = self.nearest(event.y)
  def getState(self, event):
    ''' checks if the clicked item in listbox is selected '''
    i = self.nearest(event.y)
    self.curState = self.selection_includes(i)
  def shiftSelection(self, event):
    ''' shifts item up or down in listbox '''
    i = self.nearest(event.y)
    if self.curState == 1:
      self.selection_set(self.curIndex)
    else:
      self.selection_clear(self.curIndex)
    if i < self.curIndex:
      # Moves up
      x = self.get(i)
      selected = self.selection_includes(i)
      self.delete(i)
      self.insert(i+1, x)
      if selected:
        self.selection_set(i+1)
      self.curIndex = i
    elif i > self.curIndex:
      # Moves down
      x = self.get(i)
      selected = self.selection_includes(i)
      self.delete(i)
      self.insert(i-1, x)
      if selected:
        self.selection_set(i-1)
      self.curIndex = i

root = tk.Tk()
listbox = Drag_and_Drop_Listbox(root)
for i,name in enumerate(['name'+str(i) for i in range(10)]):
  listbox.insert(tk.END, name)
  if i % 2 == 0:
    listbox.selection_set(i)
listbox.pack(fill=tk.BOTH, expand=True)
root.mainloop()      


if 0 and __name__ == "__main__":
    root = tk.Tk()
    root.title("Sequencer")
    root.geometry("%dx%d+%d+%d"%(250,800,1,0))
    s = SequencerFrame(root)
    s.pack(fill=tk.BOTH, expand=1)
    root.mainloop()
