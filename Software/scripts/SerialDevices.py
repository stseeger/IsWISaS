import serial
import time
import sys
import glob
import io

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
    
def scan_serialPorts(baudRate = [1200,9600]):
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
            info = DeviceInfo(port, bR, d.deviceName)            
            if not info.name == 'SerialDevice':
                portDict[port] = info
                deviceDict[d.deviceName] = info
    return deviceDict, portDict
    

class SerialDevice:

    NOT_CONNECTED = 0
    CONNECTED = 1
    RESPONSIVE = 2
    
    def __init__(self, port, baudrate, deviceName="SerialDevice"):

        self.deviceName = deviceName        
        print(5*"="+deviceName+(30-len(deviceName))*"=")

        # open serial port
        try:
            self.serial = serial.Serial()
            self.serial.baudrate = baudrate
            self.serial.port = port
            self.serial.open()
            self.status = SerialDevice.CONNECTED
            sys.stdout.write("   %s (%d bauds) "%(port,baudrate))
            if(deviceName=="SerialDevice"):

                for attempt in range(3):                                                        
                    deviceMessage = self.identify()
                    if len(deviceMessage) > 2:
                        break
                
                if len(deviceMessage) >= 3 and deviceMessage[0] == "deviceType:":                    
                        self.deviceName = deviceMessage[1]

                if self.deviceName == "SerialDevice":
                    print("identification failed :(")
                else:
                    print("device identified :) \n  " + self.deviceName)
                    
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
            if verbose: print("%s should be ready to use"%self.deviceName)
        else:
            self.status = SerialDevice.CONNECTED
            if verbose: print("%s  will probably not work"%self.deviceName)

        return(self.status)
#----------------------------------

class ValveController(SerialDevice):
    def __init__(self, port, baudrate):

        # open serial port via initialization method of super class
        super(ValveController, self).__init__(port, baudrate, "ValveController")

        if self.status == SerialDevice.CONNECTED:
            self.check_status(verbose=True)

    def open(self,valve):

        print("ValveController -> open %d"%valve)
        if self.status == SerialDevice.NOT_CONNECTED: return []  
        self.serial.write(("open %d\r"%(valve)).encode("utf-8"))


    def get_valveStates(self):

        if self.status == SerialDevice.NOT_CONNECTED: return []
        
        self.serial.write(b"whoisopen \r")
        return self.readComPort(500)

#------------------------------------------

class FlowController(SerialDevice):
    def __init__(self, port, baudrate, calibration=None):
                 
        self.apply_calibration(calibration)

        self.flowTargetA = 0
        self.flowTargetB = 0

        # open serial port via initialization method of super class
        super(FlowController, self).__init__(port, baudrate, "FlowController")

        # define method to be used for status checking
        self.checkRequestMethod = self._raw_get
        
        if self.status == SerialDevice.CONNECTED:
            self.serial.write(("get\r").encode("utf-8"))
            self.readComPort(500)
            self.check_status(verbose=True)

        self.lastGetTime = time.time()
        self.lastGetValueA = 0
        self.lastGetValueB = 0

    def apply_calibration(self, calibration=None):
        if calibration is None:
            self.cal = {"A":{"set_slope":1.0, "set_intercept":0.0, "get_slope":1.0,"get_intercept":0.0},
                                "B":{"set_slope":1.0, "set_intercept":0.0, "get_slope":1.0,"get_intercept":0.0}}
        else:
            self.cal = calibration["controller"]

        self.maxFlowA = 5.0 * self.cal["A"]["set_slope"] + self.cal["A"]["set_intercept"]
        self.maxFlowB = 5.0 * self.cal["B"]["set_slope"] + self.cal["B"]["set_intercept"]
        

    def _raw_get(self):
        #if self.status == SerialDevice.NOT_CONNECTED: return []
        try:
            self.serial.write(("get\r").encode("utf-8"))
            rawResult = self.readComPort(500)
            splitLine = rawResult[1].split(' ')
            try:
                self.lastGetValueA = float(splitLine[0])
                self.lastGetValueB = float(splitLine[1])
            except:
                pass
            return [rawResult]
        except:
            t = time.time()
            self.lastGetValueA = float(int(t)%60) * 8.6
            self.lastGetValueB = float(int(t+20)%70) * 8.6
            return ['#']
        

    def get(self):
        rawResult = self._raw_get()
        if len(rawResult):
            self.lastGetTime = time.time()
            A = self.lastGetValueA
            B = self.lastGetValueB
            
            A = (A-self.cal["A"]["get_intercept"])/self.cal["A"]["get_slope"]
            B = (B-self.cal["B"]["get_intercept"])/self.cal["B"]["get_slope"]

            return [round(A,2), round(B,2), self.flowTargetA, self.flowTargetB]
                
        return []

    def set(self,flowRateA = None, flowRateB = None):

        print("FlowController -> set %d %d"%(flowRateA, flowRateB))

        if flowRateB is None:
            self.flowTargetA = flowRateA
            cmd = "set A %.2f"%(flowRateA-self.cal["A"]["get_intercept"])/self.cal["A"]["get_slope"]
        elif flowRateA is None:
            self.flowTargetB = flowRateB
            cmd = "set B %.2f"%(flowRateB-self.cal["B"]["get_intercept"])/self.cal["B"]["get_slope"]
        else:
            self.flowTargetA = flowRateA
            self.flowTargetB = flowRateB
            cmd = "set %.2f %.2f"%((flowRateA-self.cal["A"]["get_intercept"])/self.cal["A"]["get_slope"],
                                   (flowRateB-self.cal["B"]["get_intercept"])/self.cal["B"]["get_slope"])
            
        if self.status == SerialDevice.NOT_CONNECTED: return
        self.serial.write(cmd.encode("utf-8"))
    
#------------------------------------------
if __name__ == "__main__":
   
    print("Available serial ports:", detect_serialPorts()) 
    deviceDict, portDict = scan_serialPorts([9600])

    #vc = ValveController(deviceDict["ValveController"].port, deviceDict["ValveController"].baudRate)
    #time.sleep(1)
    #vc.open(22)
        
            
