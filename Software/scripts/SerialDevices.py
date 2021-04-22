import serial
import time
import sys
import glob
import io
import json

def detect_serialPorts():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    devices = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            devices.append(port)
        except (OSError, serial.SerialException):
            pass
        
    return devices

class DeviceInfo:
    def __init__(self, port, baudRate, name):
        self.port = port
        self.baudRate = baudRate
        self.name = name
    
def scan_serialPorts(baudRate = [1200,9600], cachePath = None, refresh_cache = False):

    if not refresh_cache:
        # try to avoid the scan by loading from a chached scan result
        try:
            with open(cachePath,'r') as infile:
                cache = json.load(infile)
            deviceDict = cache["devices"]
            portDict   = cache["ports"]
            print("Loaded chached serial port scan results from "+ cachePath)
            return deviceDict, portDict 
        except:
            pass            

    if type(baudRate) == int:
        baudRate = [baudRate]
    print("scanning available serial ports...")
    ports = detect_serialPorts()
    deviceDict = {}
    portDict = {}
    for port in ports:
        for bR in baudRate:
            d = SerialDevice(port, bR)
            d.serial.close()
            info = {"port" : port, "baudRate" : bR, "name" : d.deviceType}
            if not info["name"] == 'SerialDevice':
                portDict[port] = info
                deviceDict[d.deviceType] = info

    try:
        with open(cachePath,'w') as outfile:
            json.dump({"devices":deviceDict, "ports":portDict}, outfile)
        print("Serial port scan results stored in " + cachePath)
    except:
        print("Serial port scan results could not be stored in " + cachePath)

    return deviceDict, portDict

def find_device(name, baudRate = [1200, 9600], cachePath = None):
    
    deviceDict, portDict = scan_serialPorts(baudRate, cachePath)

    if name in deviceDict.keys():
        return deviceDict[name]

    deviceDict, portDict = scan_serialPorts(baudRate, cachePath, refresh_cache=True)

    if name in deviceDict.keys():
        return deviceDict[name]

    return None
    

class SerialDevice:

    NOT_CONNECTED = 0
    CONNECTED = 1
    RESPONSIVE = 2
    
    def __init__(self, port, baudrate, deviceType="SerialDevice"):

        self.deviceType = deviceType
        self.deviceModel = "?"
        self.deviveFirmwareVersion = "?"
        print(5*"="+deviceType+(30-len(deviceType))*"=")

        # open serial port
        try:
            self.serial = serial.Serial()
            self.serial.baudrate = baudrate
            self.serial.port = port
            self.serial.open()
            self.status = SerialDevice.CONNECTED
            sys.stdout.write("   %s (%d bauds) "%(port,baudrate))
            if(deviceType=="SerialDevice"):
               
                for attempt in range(3):                                                        
                    deviceMessage = self.identify()
                    if len(deviceMessage) > 2:
                        break
                    time.sleep(0.1)
                
                if len(deviceMessage) >= 3 and deviceMessage[0] == "?":                        
                        deviceInfo = deviceMessage[1].split(' ')                        
                        self.deviceType = deviceInfo[0]
                        self.deviceModel = deviceInfo[1]
                        self.deviveFirmwareVersion = deviceInfo[2]

                if self.deviceType == "SerialDevice":
                    print("identification failed :(")
                else:
                    print("device identified :) \n  " + self.deviceType)
                    
        except:
            self.status = SerialDevice.NOT_CONNECTED
            print("connection failed :(")
        
        
        self.checkRequestMethod = self.identify   

    def readComPort(self, sleeptime = 0):

        #if self.status == SerialDevice.NOT_CONNECTED: return
        
        time.sleep(sleeptime/1000)
        bytesToRead = self.serial.inWaiting()
        result = self.serial.read(bytesToRead).decode('utf-8').split('\r\n')
        return(result)    

    def identify(self):
        self.serial.write(b"?\r")
        return self.readComPort(300)

    def check_status(self, verbose=False):

        try:
           self.serial.inWaiting()
        except:
            self.status=SerialDevice.NOT_CONNECTED
            return(SerialDevice.NOT_CONNECTED)

        for tryCount in range(5):
            requestResult = self.checkRequestMethod()
            if not requestResult is None and len(requestResult): break
            time.sleep(0.1)
    
        if not requestResult is None and len(requestResult):
            self.status = SerialDevice.RESPONSIVE
            if verbose: print("%s should be ready to use"%self.deviceType)
        else:
            self.status = SerialDevice.CONNECTED
            if verbose: print("%s  will probably not work"%self.deviceType)

        return(self.status)
#----------------------------------

class IsWISaS_Controller(SerialDevice):

    def __init__(self, port, baudrate, flowCalibration = None):
        super(IsWISaS_Controller, self).__init__(port, baudrate, "IsWISaS_Controller")

        self.set_flowCalibration(flowCalibration)

        self.flowTargetA = 0
        self.flowTargetB = 0

        self.box  = 0
        self.valve = 0

        self.maxFlowA = 255 * self.flowCalibration["A"]["set_slope"]
        self.maxFlowB = 255 * self.flowCalibration["B"]["set_slope"]

    def get_something(self, cmd, attempts=3, waitTime=500):

        for attempt in range(attempts):
            self.serial.write(("%s\r"%(cmd)).encode("utf-8"))
            response = self.readComPort(500)
            if len(response) > 2 and response[-1] == ">> " and response[-3].endswith(cmd):
                return response[-2]

        return None

    # ------- valve section -----------------
    def set_valve(self, valve, verbose=True):
        if not self.status: return

        try:
            splitValve = valve.split("#")
            box   = int(splitValve[0])
            valve = int(splitValve[1])
            print(">> valve %d#%d"%(box,valve))
            self.serial.write(("valve %d#%d\r"%(box,valve)).encode("utf-8"))
            self.box = box
            self.valve = valve
        except:
            valve = int(valve)
            print(">> valve %d"%(valve))
            self.serial.write(("valve %d\r"%(valve)).encode("utf-8"))
            self.box = 0
            self.valve = valve

    def get_valve(self):
        response = self.get_something("valve")

        try:
            return int(response.replace("valve>",""))
        except:
            return response        

    # ------- flow section -------------------

    def set_flowCalibration(self, calibration=None):
        if calibration is None:
            self.flowCalibration = {"A":{"set_slope":1.0,
                                         "set_intercept":0.0,
                                         "get_slope":1.0,
                                         "get_intercept":0.0},                                         
                                    "B":{"set_slope":1.0,
                                         "set_intercept":0.0,
                                         "get_slope":1.0,
                                         "get_intercept":0.0}
                                    }
        else:
            self.flowCalibration = calibration

        self.maxFlowA = 255 * self.flowCalibration["A"]["set_slope"]
        self.maxFlowB = 255 * self.flowCalibration["B"]["set_slope"]


    def get_flow(self, decimalPlaces=1):
        response = self.get_something("flow")
        
        try:
            result = [float(x) for x in response.replace("flow>","",).split("|")]
            fc = self.flowCalibration
            flowA = round(result[0] * fc["A"]["get_slope"] + fc["A"]["get_intercept"], decimalPlaces)
            flowB = round(result[1] * fc["B"]["get_slope"] + fc["B"]["get_intercept"], decimalPlaces)
            return [flowA, flowB]
        except:
            return response

    def set_flow(self, flowA, flowB = 0):
        print(">> flow %d %d"%(flowA, flowB))

        if self.status == SerialDevice.NOT_CONNECTED:
            print("!! no serial connection to device !!")
            return
        
        fc = self.flowCalibration
        flowA = int((flowA+ fc["A"]["set_intercept"]) / fc["A"]["set_slope"])
        flowB = int((flowB+ fc["B"]["set_intercept"]) / fc["B"]["set_slope"])

        self.flowTargetA = flowA
        self.flowTargetB = flowB

        cmd = "flow %d %d\r"%(flowA, flowB)       
        self.serial.write(cmd.encode("utf-8"))
 
#------------------------------------------
if __name__ == "__main__":
   
    print("Available serial ports:", detect_serialPorts()) 
    #deviceDict, portDict = scan_serialPorts([9600], cachePath = "../temp/serial.cch")

    d = find_device("IsWISaS_Controller", baudRate = [9600], cachePath = "../temp/serial.cch")

    c = IsWISaS_Controller(d["port"],
                           d["baudRate"],
                           flowCalibration = {"A":{"set_slope":0.721, "set_intercept":0, "get_slope":0.721, "get_intercept":0},
                                              "B":{"set_slope":0.177, "set_intercept":0, "get_slope":0.177, "get_intercept":0}
                                              }
                           )
        
            
