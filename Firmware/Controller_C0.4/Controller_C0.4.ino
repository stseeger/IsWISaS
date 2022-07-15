#include "src/CmdArduino//Cmd.h"
#include <SoftwareSerial.h>

#define DEVICE "IsWISaS_Controller"
#define MODEL "C"
#define VERSION "0.4"

#define INPUT_BUFFER_SIZE 32
char inputBuffer[INPUT_BUFFER_SIZE];
char boxBuffer[3];
char slotBuffer[3];
char checksumBuffer[3];

/*-----( Declare Constants and Pin Numbers )-----*/
#define portOne_RX 12  //Serial Receive pin
#define portOne_TX A0  //Serial Transmit pin
#define portOne_EN 13  //RS485 Direction control

#define portTwo_RX A4  //Serial Receive pin
#define portTwo_TX A3  //Serial Transmit pin
#define portTwo_EN A2  //RS485 Direction control

#define RS485Transmit    HIGH
#define RS485Receive     LOW
#define RS485_BAUDRATE 1200
/*-----( Declare objects )-----*/
SoftwareSerial portOne(portOne_RX, portOne_TX);
SoftwareSerial portTwo(portTwo_RX, portTwo_TX);
/*-----------------------------------------*/
struct valveSlotType{
  byte box;
  byte slot;  
};

//----------------------------------------



//------- valve control stuff ----------------
#define VALVE_COUNT 8
int valvePins[VALVE_COUNT] = {9, 8, 7, 10, 11, 4, 3, 2};

valveSlotType primaryValve   = {1,1};
valveSlotType groupValve     = {0,0};

//.........................................
valveSlotType parse_valveSlot(char *arg){
  valveSlotType valveSlot;
  byte value;
  char *pch;
  pch = strtok(arg,"#");
  for(byte i=0; i<2; i++){
    if(pch == NULL) break;
    value =  atoi(pch);
    
    if(i==0){
      valveSlot.slot = value;
      valveSlot.box = 0;
    }else{
      valveSlot.box = valveSlot.slot;
      valveSlot.slot = value;
    }   
    pch = strtok(NULL, "#");
  }
  return valveSlot;
}

//.........................................
void update_valves(){
  for(byte i=0; i < VALVE_COUNT; i++){
        digitalWrite(valvePins[i], ((primaryValve.box==0)   & (i == primaryValve.slot-1))|                                   
                                   ((groupValve.box==0)     & (i == groupValve.slot-1)));
  }  

  
  SoftwareSerial SWSPort[2] = {portOne, portTwo};
  int SWS_EN_PIN[2] = {portOne_EN, portTwo_EN};
  
  for(byte n=0; n<2; n++){
    digitalWrite(SWS_EN_PIN[n],HIGH);
    delay(50);
    SWSPort[n].print("valve ");
    SWSPort[n].print(primaryValve.box);
    SWSPort[n].print('#');
    SWSPort[n].print(primaryValve.slot);
    SWSPort[n].print('#');
    SWSPort[n].print(groupValve.box);
    SWSPort[n].print('#');
    SWSPort[n].println(groupValve.slot);
    digitalWrite(SWS_EN_PIN[n],LOW);   
 } 
}

//.........................................
void get_activeValve(){  
  Serial.print("valve>");
  Serial.print(primaryValve.box);
  Serial.print('#');
  Serial.print(primaryValve.slot);  

  Serial.print(' ');
  Serial.print(groupValve.box);
  Serial.print('#');
  Serial.print(groupValve.slot);
  
  Serial.println();
}

//------- flow control stuff  ----------------
#define PWM_PIN_A 5
#define ANA_PIN_A A6

#define PWM_PIN_B 6
#define ANA_PIN_B A7

#define PERIOD 1e2
#define SAMPLES 100

float valueA = 0;
float valueB = 0;

void set_pwmPin(byte pin, int value){
  if(value < 0) value = 0;
  if(value >1023) value = 1023;
  analogWrite(pin, value);
}

//......................................
void measure_anaPins(){
  unsigned long sumA = 0;
  unsigned long sumB = 0;

  for(int i=0; i< SAMPLES; i++){
    sumA+=analogRead(ANA_PIN_A);
    sumB+=analogRead(ANA_PIN_B);
  }

  valueA = float(sumA)/float(SAMPLES)/4;
  valueB = float(sumB)/float(SAMPLES)/4;
  
}

void open_RS485(byte port){
  if(port==1){
    digitalWrite(portOne_EN,HIGH);    
  }
  if(port==2){
    digitalWrite(portTwo_EN,HIGH);
  }
  delay(50);
}

void close_RS485(byte port){
  if(port==1){
    digitalWrite(portOne_EN,LOW);    
  }
  if(port==2){
    digitalWrite(portTwo_EN,LOW);
  }
}

byte get_RS485Response(byte portNumber){
  byte responseLength=0;
  if(portNumber==1){      
      responseLength = portOne.readBytesUntil('\0',inputBuffer,INPUT_BUFFER_SIZE-1); 
  }
  if(portNumber==2){
    responseLength = portTwo.readBytesUntil('\0',inputBuffer,INPUT_BUFFER_SIZE-1);
  }

  if(responseLength){
    inputBuffer[responseLength-1]='\0';
    byte offset=0;
    for(byte i=0; i<responseLength;i++){
      if(inputBuffer[offset]=='<') break;
      offset++;
    }    
    Serial.println(inputBuffer+offset);
    inputBuffer[0]='\0';
  }else{
    Serial.println("< x");
  } 

   return responseLength;
}



//==========================================

void cmd_identify(int arg_cnt, char **args){

  byte targetID = 0;
  if(arg_cnt>1) targetID = atoi(args[1]);

  if(targetID){
    SoftwareSerial SWSPort[2] = {portOne, portTwo};
    byte responseLength = 0;
    for(byte i=0; i<2; i++){
      open_RS485(i+1);
        SWSPort[i].print("? ");
        SWSPort[i].println(targetID);
      close_RS485(i+1);
      delay(20);
      responseLength = get_RS485Response(i+1);
      if(responseLength) break;
    }
    return;
  }
  
  Serial.print(DEVICE);
  Serial.print(' ');
  Serial.print(MODEL);
  Serial.print(' ');
  Serial.println(VERSION);  
}

//......................................
void cmd_scan(int arg_cnt, char **args){
  
  byte boxID = 0;
  
  if(arg_cnt==2){
    boxID =  atoi(args[1]);
  }  

  if(boxID==0){    
    Serial.print(VALVE_COUNT);
    Serial.print(";");
    Serial.println(VALVE_COUNT);
    return;
  }  

  SoftwareSerial SWSPort[2] = {portOne, portTwo};
  byte responseLength = 0;
  for(byte i=0; i<2; i++){
    open_RS485(i+1);
    SWSPort[i].print("?? ");
    SWSPort[i].println(boxID);
    close_RS485(i+1);
    delay(20);
    responseLength = get_RS485Response(i+1);
    if(responseLength) break;
  }
}
//......................................
void cmd_valve(int arg_cnt, char **args){

  // in case no second argument was passed, just print the active valve
  if(arg_cnt < 2){
    get_activeValve();
    return;
  }
  primaryValve = parse_valveSlot(args[1]);
  
  if(arg_cnt > 2)
    groupValve = parse_valveSlot(args[2]);
  
  update_valves();  
}

//........................................
void cmd_test(int arg_cnt, char **args){
  
  if(arg_cnt > 1){
    byte targetID = atoi(args[1]);
    if(targetID){      
      SoftwareSerial SWSPort[2] = {portOne, portTwo};      
      for(byte i=0; i<2; i++){
        open_RS485(i+1);
          SWSPort[i].print("test ");
          SWSPort[i].println(targetID);
        close_RS485(i+1);
      }      
      return;
    } 
  }  
  
  valveSlotType backupPrimaryValve = {primaryValve.box, primaryValve.slot};
  primaryValve.box=16;

    for(byte n=0; n<VALVE_COUNT; n++){    
      primaryValve.slot=(n+1);
      update_valves();
      delay(500);
    }

   primaryValve.box = backupPrimaryValve.box;
   primaryValve.slot = backupPrimaryValve.slot;
}
//........................................

void cmd_flow(int arg_cnt, char **args){
  
  // in case no further argument were passed, just print the current analog voltages of the analog pins
  if(arg_cnt != 3){
    measure_anaPins();
    Serial.print("flow>");
    Serial.print(valueA);
    Serial.print("|");
    Serial.println(valueB);
    return;
  }
  
  // in case the second argument was 'A', interpret the third as target value for A
  if(args[1][0] == 'A'){
    set_pwmPin(PWM_PIN_A, atoi(args[2]));
    return;
  }

  // in case the second argument was 'B', interpret the third as target value for B
  if(args[1][0] == 'B'){
    set_pwmPin(PWM_PIN_B, atoi(args[2]));
    return;
  }

  // otherwise
  set_pwmPin(PWM_PIN_A, atoi(args[1]));
  set_pwmPin(PWM_PIN_B, atoi(args[2]));
}
//-----------------------------
void setup() {
  cmdInit(9600);  
  cmdAdd("?", cmd_identify);
  cmdAdd("??", cmd_scan);
  cmdAdd("test", cmd_test);
  cmdAdd("valve", cmd_valve);
  cmdAdd("flow", cmd_flow);  

  // Software Serial
  pinMode(portOne_EN, OUTPUT);
  pinMode(portTwo_EN, OUTPUT);
  portTwo.begin(RS485_BAUDRATE); // Start the software serial port
  portOne.begin(RS485_BAUDRATE); // Start the software serial port
  
  for(byte i = 0; i<VALVE_COUNT; i++){
    pinMode(valvePins[i], OUTPUT);
    digitalWrite(valvePins[i], LOW);
  }
  //pinMode(BOX0_FLUSH_VALVE, OUTPUT);
  //digitalWrite(BOX0_FLUSH_VALVE, LOW);
  
  update_valves();
  cmd_identify(0,NULL);
  Serial.print(">> ");
}

//------------------------------

void loop() {
  cmdPoll();
}
