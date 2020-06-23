import serial
import time
import sys
import glob
import io
import SerialDevices

#------------------------------------------
class SierraFlowController():

    NOT_CONNECTED = -1
    CONNECTED = 0
    RESPONSIVE = 1
    
    remaining=bytes()
    cr = '\r'.encode('ascii')
    
    def __init__(self, port, baudrate, maxFlowRate):
        self.port = port
        self.baudrate = baudrate
        self.maxFlowRate = maxFlowRate

        self.lastGetValueA = 0
        self.lastGetValueB = 0
        self.lastGetTime = time.time()
        self.flowTargetA = 0
        self.flowTargetB = 0

        deviceName = "Sierra_FlowController"
        print(5*"="+deviceName+(30-len(deviceName))*"=")
        sys.stdout.write("   %s (%d bauds) "%(port,baudrate))

        try:
            self.connection=serial.Serial(port, 9600, timeout=2)
            self.status = self.check_status()
            print("connection established :)")
        except:
            self.status = SierraFlowController.NOT_CONNECTED
            print("connection failed :(")

    def check_status(self):        

        try:
            x = self.get()
            self.lastGetTime = time.time()
            if len(x):
                self.lastGetValueA = x[-1]
                return SierraFlowController.RESPONSIVE
            else:
                return SierraFlowController.CONNECTED
        except:
            self.status = SierraFlowController.NOT_CONNECTED
            return self.status            
        
        
    def __del__(self):
        self.connection.close()

    def calculate_CRC(self, string):
        """ Calculate the CRC
        string is what it calculates the CRC of
        It returns the CRC as two bytes """

        crc = 0xffff
        for char in string:
            crc ^= char * 0x0100
            for i in range(8):
                if (crc & 0x8000) == 0x8000:
                    crc = ((crc<<1)^0x1021) & 0xffff
                else:
                    crc = (crc<<1) & 0xffff
        if (crc & 0xff00) == 0x0d00:
            crc += 0x0100
        if (crc & 0xff00) == 0x0000:
            crc += 0x0100
        if (crc & 0x00ff) == 0x000d:
            crc += 0x0001
        if (crc & 0x00ff) == 0x0000:
            crc += 0x0001
        byte1 = (crc & 0xff00)//0x0100
        byte2 = crc & 0x00ff        

        return bytearray((byte1, byte2))

    def send_command(self, command):
        if not isinstance(command, bytes):
            command = command.encode('ascii')
        crc = self.calculate_CRC(command)
        self.connection.write(command + crc + self.cr)

    def read_commands(self):
        values = self.connection.read(50).split(self.cr)
        values[0] = self.remaining + values[0]
        self.remaining = values[-1]
        return values[0:-1]

    def get(self):
        self.send_command("?Flow")
        received = self.read_commands()
        receivedDecoded = [x[:-2].decode('ascii') for x in received]        
        result=-99
        if len(receivedDecoded):
            try:
                result = float(receivedDecoded[-1].replace("Flow",""))
            except:
                pass

        self.lastGetValueA = result
        self.lastGetTime = time.time()
        
        print("get: %.2f"%result)
        return [self.lastGetValueA, 0, self.flowTargetA, 0]
        
        return [-99 for x in receivedDecoded]


    def set(self,flowRateA = None, flowRateB = None):
        
        print("FlowController -> set %d"%flowRateA)
        if not flowRateB is None:
            print("\t!!! second flow rate is ignored !!!")

        self.flowTargetA = flowRateA
        self.flowTargetB = 0
        self.lastGetValueB = 0
        

        command = "!Sinv%.2f"%flowRateA
        self.send_command(command)
        received = self.read_commands()
        receivedDecoded = [x[:-2].decode('ascii') for x in received]
        print("set:"+ "> ".join([""] + receivedDecoded))

class AnalytMTCFlowController():
    NOT_CONNECTED = -1
    CONNECTED = 0
    RESPONSIVE = 1

    def __init__(self, port, baudrate, maxFlowRate):
        self.port = port
        self.baudrate = baudrate
        self.maxFlowRate = maxFlowRate

        self.lastGetValueA = 0
        self.lastGetValueB = 0
        self.lastGetTime = time.time()
        self.flowTargetA = 0
        self.flowTargetB = 0

        self.rawBuffer = ""

        deviceName = "AnalytMTC_FlowController"
        print(5*"="+deviceName+(30-len(deviceName))*"=")
        sys.stdout.write("   %s (%d bauds) "%(port,baudrate))        

        try:
            self.connection=serial.Serial(port, baudrate, timeout=2)
            self.status = SerialDevice.RESPONSIVE
            print("connection established :)")
        except:
            self.status = SerialDevice.NOT_CONNECTED
            print("connection failed :(")

    def check_status(self):
        return self.status

    def parseLine(self, line):
        splitLine = line.split()        
        if len(splitLine) == 6:
            parsedLine = list(map(lambda x: float(x), splitLine[:5]))                        
            return parsedLine

    def get(self):

        bytesToRead = self.connection.inWaiting()
        x = None
        if bytesToRead:
            self.rawBuffer += self.connection.read(bytesToRead).decode('utf-8')
            splitLine = self.rawBuffer.split('\r')
            if len(splitLine) > 1:
                x = self.parseLine(splitLine[0])
                self.rawBuffer = splitLine[-1]

        if not x is None:                
            self.lastGetTime = time.time()
            return [x[3], 0, self.flowTargetA, 0]
        return []

    def set(self,flowRateA = None, flowRateB = None):

        print("FlowController -> set %d"%(flowRateA))
        self.flowTargetA = flowRateA

        value = int(flowRateA * 64000/self.maxFlowRate)
        self.connection.write(("%d\r\n"%value).encode("utf-8"))

        return

    
        # this stuff is for later, when two flow controllers are controlled at once...
        print("FlowController -> set %d %d"%(flowRateA, flowRateB))

        if flowRateB is None:
            self.flowTargetA = flowRateA
            cmd = "set A %.0f"%flowRateA
        elif flowRateA is None:
            self.flowTargetB = flowRateB
            cmd = "set B %.0f"%flowRateB
        else:
            self.flowTargetA = flowRateA
            self.flowTargetB = flowRateB
            cmd = "set %.0f %.0f"%(flowRateA, flowRateB)
            
        if self.status == SerialDevice.NOT_CONNECTED: return
        self.serial.write(cmd.encode("utf-8"))
    
#------------------------------------------
if __name__ == "__main__":

    if 0:        
        port = "COM19"
        unit = AnalytMTCFlowController(port,19200,200)
        for i in range(50,1,-1):        
            unit.set(i*4)
            for n in range(4):
                time.sleep(1)
                print(unit.get())        
            
           # unit.get()
    else:
        deviceDict, portDict = SerialDevices.scan_serialPorts([9600])  
        d = SerialDevices.detect_serialPorts()        
        
            
