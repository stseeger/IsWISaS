Each of the different controller types should respond to the same set of serial text commands:  
  
**?**: return device class, devce type and version (seperated by spaces)  
**valve**: return the active valve  
**valve #**: activate valve # and close previous active valve  
**flow**: return the analog voltages (in mV) returned by the two mass flow controllers (seperated by spaces)  
**flow a b**: change the set point voltages (a and b in mV) to the two flow controllers (A and B)  
