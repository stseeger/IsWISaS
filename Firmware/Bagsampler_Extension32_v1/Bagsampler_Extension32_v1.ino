#include "src/CmdArduino//Cmd.h"

#define DEVICE "Bagsampler_Extension"
#define MODEL "C"
#define VERSION "1"

#define RS485_BAUDRATE 1200
#define RS485_MODE_CONTROL_PIN 13

#define INPUT_BUFFER_SIZE 32
char inputBuffer[INPUT_BUFFER_SIZE];

#define M1 10
#define M2 11
#define M3 12
#define M4 A0

#define N1 2
#define N2 3
#define N3 4
#define N4 5
#define N5 6
#define N6 7
#define N7 8
#define N8 9

#define VALVE_COUNT 32
const int primaryValvePins[VALVE_COUNT]   = {M1, M1, M1, M1, M1, M1, M1, M1,  M2, M2, M2, M2, M2, M2, M2, M2,  M3, M3, M3, M3, M3, M3, M3, M3,  M4, M4, M4, M4, M4, M4, M4, M4};
const int secondaryValvePins[VALVE_COUNT] = {N1, N2, N3, N4, N5, N6, N7, N8,  N1, N2, N3, N4, N5, N6, N7, N8,  N1, N2, N3, N4, N5, N6, N7, N8,  N1, N2, N3, N4, N5, N6, N7, N8};

#define ID_PIN A3
#define ANALOG_ID_TOLERANCE 7
#define ID_TABLE_SIZE 16
const int analogIdVals[ID_TABLE_SIZE] = {   0,  45,  90, 129, 182, 214, 245, 272,
                                          330, 352, 374, 393, 420, 436, 453, 468};

struct valveSlotType{
  byte box;
  byte slot;  
};

valveSlotType valve   = {0,1};

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
        digitalWrite(primaryValvePins[i],   ((valve.box == id)   & (i == valve.slot-1)));
        digitalWrite(secondaryValvePins[i], ((valve.box == id)   & (i == valve.slot-1)));
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

  valve = parse_valveSlot(args[1]);
  update_valves();
}
//--------------------------------------------
void cmd_identify(int arg_cnt, char **args){
  Serial.print(DEVICE);
  Serial.print(" ");
  Serial.print(MODEL);
  Serial.print(" ");
  Serial.print(VERSION);  
  Serial.print(" ");
  Serial.println(get_id());
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
    pinMode(primaryValvePins[i], OUTPUT); 
    pinMode(secondaryValvePins[i], OUTPUT); 
    digitalWrite(primaryValvePins[i], LOW);
    digitalWrite(secondaryValvePins[i], LOW);
  }

  cmd_identify(0,NULL);
 
  update_valves();
} 
//-------------------------------
 
void loop() 
{ 

  byte n=0;
  for(byte i=0; i < VALVE_COUNT; i++){
    digitalWrite(primaryValvePins[i], i==n);
    digitalWrite(secondaryValvePins[i], i==n);
  }
   
  if(get_id()<16){
    //RS485Poll();
    //update_valves();
  }else{
    for(byte n=0; n<VALVE_COUNT; n++){
        for(byte i=0; i < VALVE_COUNT; i++){
          digitalWrite(primaryValvePins[i], i==n);
          digitalWrite(secondaryValvePins[i], i==n);
        }
      delay(400);
      digitalWrite(primaryValvePins[n], LOW);
      digitalWrite(secondaryValvePins[n], LOW);
      delay(100);
    }
  }
} 
