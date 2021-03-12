#include "src/CmdArduino/Cmd.h"


#define DEVICE "IsWISaS_Extension"
#define MODEL "C"
#define VERSION "1.0"

#define ID_PIN A3
#define ANALOG_ID_TOLERANCE 5

// pins to control the valves
#define VALVE_COUNT 8
const int valvePins[8] = {9,8,7,6,5,4,3,2};

const int analogIdVals[16] = {   0,  45,  90, 129, 182, 214, 245, 272,
                               330, 352, 374, 393, 420, 436, 453, 468};
byte activeValve = 1;
byte id = 0;

//=== serial communication ===========

void cmd_identify(int arg_cnt, char **args){
  Serial.print(DEVICE);
  Serial.print(" ");
  Serial.print(MODEL);
  Serial.print(" ");
  Serial.println(VERSION);  
}

void cmd_valve(int arg_cnt, char **args){
      
  if(arg_cnt>2){
    Serial.println(activeValve);
    return;    
  }
  
  int v = cmdStr2Num(args[arg_cnt-1], 10);
  if(v < 1 | v > VALVE_COUNT) return;
  
  activeValve = v;
  for(byte i=0; i < VALVE_COUNT; i++){
    digitalWrite(valvePins[i], i==(v-1));   
  }  
}

//---------------------------------------
byte get_id(){
  int analogReading = analogRead(ID_PIN);
  for(byte i=0; i<16; i++){
    if(analogReading >= (analogIdVals[i] - ANALOG_ID_TOLERANCE)&
       analogReading <= (analogIdVals[i] + ANALOG_ID_TOLERANCE)){
          return(i);          
       }
  }
  return(0);
}
//=== setup and main loop================

void setup()
{ 
  //Timer1.initialize(100); // 100 µs -> 10 kHz
  cmdInit(9600);
  cmdAdd("?", cmd_identify);
  cmdAdd("valve", cmd_valve);
  for(byte i=0; i < VALVE_COUNT; i++){
    pinMode(valvePins[i], OUTPUT);    
    digitalWrite(valvePins[i], i == (activeValve-1));
  }  
  cmd_identify(0,NULL);
  for(byte i=0; i<30; i++)Serial.print('=');
  Serial.print("\n>> ");
}

void loop() { 
  for(byte i=0; i < VALVE_COUNT; i++){
    digitalWrite(valvePins[i], i == id  || i == (id+8));
  }
  delay(500);

  for(byte i=0; i < VALVE_COUNT; i++){
    digitalWrite(valvePins[i], i == id);
  }
  delay(500);
    
  id = get_id();
}
