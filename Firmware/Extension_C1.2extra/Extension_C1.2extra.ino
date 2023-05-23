#include "src/CmdArduino//Cmd.h"

#define DEVICE "IsWISaS_Extension"
#define MODEL "C"
#define VERSION "1.2extra"

#define RS485_BAUDRATE 1200
#define RS485_MODE_CONTROL_PIN 13

#define INPUT_BUFFER_SIZE 32
char inputBuffer[INPUT_BUFFER_SIZE];

#define VALVE_COUNT 8
const int valvePins[VALVE_COUNT] = {2, 3, 4, 5, 6, 7, 8, 9};

#define DRAIN_VALVE_A 12
#define DRAIN_VALVE_B A0
#define DRAIN_MILLISECONDS 5000

#define ID_PIN A3
#define ANALOG_ID_TOLERANCE 7
#define ID_TABLE_SIZE 16
const int analogIdVals[ID_TABLE_SIZE] = {   0,  45,  90, 129, 182, 214, 245, 272,
                                          330, 352, 374, 393, 420, 436, 453, 468};
                                          
struct valveSlotType{
  byte box;
  byte slot;  
};

unsigned long drainStart=0;
bool drainTriggerSet = false;

valveSlotType primaryValve   = {0,9};
valveSlotType secondaryValve = {0,0};

byte id = 0;

//--------------------------------------------
byte get_id(){
  int analogReading = analogRead(ID_PIN);
  for(byte i=0; i<ID_TABLE_SIZE; i++){
    if(analogReading >= (analogIdVals[i] - ANALOG_ID_TOLERANCE)&
       analogReading <= (analogIdVals[i] + ANALOG_ID_TOLERANCE)){
          return(i+1);          
       }
  }
  return(0);
}
//--------------------------------------------
void update_valves(){

   id = get_id();
  
  for(byte i=0; i < VALVE_COUNT; i++){
        digitalWrite(valvePins[i], ((primaryValve.box == id)   & (i == primaryValve.slot-1)) |
                                   ((secondaryValve.box == id) & (i == secondaryValve.slot-1)));
  }

  if((primaryValve.box==id & primaryValve.slot==VALVE_COUNT) |
     (secondaryValve.box==id & secondaryValve.slot==VALVE_COUNT)){
    drainTriggerSet=true;
  }
  
  if(drainTriggerSet & !((primaryValve.box==id | secondaryValve.box==id))){                         
    drainStart=millis();
    drainTriggerSet = false;
  }

  if(drainStart>0){
    unsigned long timeDiff = millis() - drainStart;
    digitalWrite(DRAIN_VALVE_A, timeDiff < DRAIN_MILLISECONDS);
    digitalWrite(DRAIN_VALVE_B, (timeDiff > DRAIN_MILLISECONDS) & (timeDiff < 2*DRAIN_MILLISECONDS));
    if(timeDiff > 2*DRAIN_MILLISECONDS) drainStart=0;
  }else{
    digitalWrite(DRAIN_VALVE_A, LOW);
    digitalWrite(DRAIN_VALVE_B, LOW);
  }
  
}
//--------------------------------------------
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
//--------------------------------------------
void cmd_valve(int arg_cnt, char **args){

  // in case no second argument was passed return
  if(arg_cnt < 2){    
    return;
  }
  primaryValve = parse_valveSlot(args[1]);

  if(arg_cnt >2)
    secondaryValve = parse_valveSlot(args[2]);
}
//--------------------------------------------
void cmd_identify(int arg_cnt, char **args){
  Serial.print(DEVICE);
  Serial.print(" ");
  Serial.print(MODEL);
  Serial.print(" ");
  Serial.println(VERSION);
}
//--------------------------------------------
void RS485Poll(){

  if(!Serial.available()) return;
  
  int n = Serial.readBytesUntil(13,inputBuffer,INPUT_BUFFER_SIZE-2);  
  inputBuffer[n] = '\n';
  inputBuffer[n+1] = '\0';

  if(inputBuffer[n] != '\n' | inputBuffer[0] == '\n') return;
  
  byte i=0;
  if(inputBuffer[0]!='\n') while(i<INPUT_BUFFER_SIZE){
    if(inputBuffer[i]=='\0') break;
    //Serial.print(inputBuffer[i]);
    i++;       
  }      
  cmd_parse(inputBuffer);
  while(Serial.available()){
    Serial.read();
  }
}
//--------------------------------------------
void setup() 
{ 
  cmdInit(RS485_BAUDRATE);
  cmdAdd("?", cmd_identify);
  cmdAdd("valve", cmd_valve);
  
  pinMode(RS485_MODE_CONTROL_PIN, OUTPUT);
  digitalWrite(RS485_MODE_CONTROL_PIN, LOW); // set RS485_module to receive mode

  for(byte i=0; i < VALVE_COUNT; i++){
    pinMode(valvePins[i], OUTPUT);    
    digitalWrite(valvePins[i], LOW);
  }
  pinMode(DRAIN_VALVE_A,OUTPUT);
  pinMode(DRAIN_VALVE_B,OUTPUT);
  digitalWrite(DRAIN_VALVE_A, LOW);
  digitalWrite(DRAIN_VALVE_B, LOW);
  

  cmd_identify(0,NULL);
 
  update_valves();
} 
//-------------------------------
 
void loop() 
{ 
  if(get_id()<16){
    RS485Poll();
    update_valves();
  }else{
    for(byte n=0; n < VALVE_COUNT; n++){
        for(byte i=0; i < VALVE_COUNT; i++){
          digitalWrite(valvePins[i], i==n);
      }
      delay(400);
      digitalWrite(valvePins[n], LOW);
      delay(100);
    }
  }
} 
