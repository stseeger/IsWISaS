#include "src/CmdArduino//Cmd.h"

#define DEVICE "Bagsampler"
#define MODEL "MEGA_32_standalone"
#define VERSION "1.0"


#define VALVE_COUNT 32
const int valvePins[VALVE_COUNT]   = {22,23,24,25,26,27,28,29, 30,31,32,33,34,35,36,37, 38,39,40,41,42,43,44,45, 46,47,48,49,50,51,52,53};

struct valveSlotType{
  byte box;
  byte slot;  
};

valveSlotType valve   = {0,1};

byte id = 0;

//--------------------------------

void get_activeValve(){
  Serial.print("valve>");
  Serial.print(valve.box);
  Serial.print('#');
  Serial.print(valve.slot); 
  Serial.println();
}

//--------------------------------------------
void update_valves(){
  for(byte i=0; i < VALVE_COUNT; i++){
        digitalWrite(valvePins[i],   !(((valve.box == id)   & (i == valve.slot-1))));        
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

  // in case no second argument was passed, just print the active valve
  if(arg_cnt < 2){    
    get_activeValve();
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
  Serial.println(VERSION);  
  
}
//-------------------------------------------
void cmd_demo(int arg_cnt, char **args){
   
   valveSlotType valveBackup = valve;
   
   for(byte i=0; i < VALVE_COUNT; i++){
       valve.slot = i+1;
       update_valves();
       delay(250);
  }

  valve = valveBackup;
  update_valves();

}

//--------------------------------------------
void setup() 
{ 
  cmdInit(9600);
  cmdAdd("?", cmd_identify);
  cmdAdd("valve", cmd_valve);   
  cmdAdd("demo", cmd_demo);

  for(byte i=0; i < VALVE_COUNT; i++){
    pinMode(valvePins[i], OUTPUT);    
    digitalWrite(valvePins[i], HIGH);    
  }

  cmd_identify(0,NULL);
 
  update_valves();
} 
//-------------------------------
 
void loop() 
{ 
    cmdPoll();
} 
