//#include "TimerOne.h"
#include <Cmd.h>

// PWM pins for the RC-circuits
#define PWM_A 5
#define PWM_B 6

// analog pins for reading the flow controllers' feedback
#define ANA_A A0
#define ANA_B A1


// pins to control the valves
#define VALVE_COUNT 16
const byte valvePins[16] = { 9,  8,  7,  10,  11,  4,  3,  2,
                            A2, A3, A4,  A5,  A6, A7, 12, 13};

// varaibles to save target flow values and actual flow rates
float recentA = 0;
float recentB = 0;
float targetA = 0;
float targetB = 0;
                                                        
#define SAMPLES 100 // number of samples for flow rate measurements

//=== serial communication ===========

//>> ? -> return device type
void cmd_identify(int arg_cnt, char **args){
  Serial.print("deviceType:");
  arg_cnt==1 ? Serial.print(' ') : Serial.println();
  Serial.println("Controller_A1.0");
}

//>> set -> set flow target values
void cmd_set(int arg_cnt, char **args){

  // in case two numbers were passed, set target A and B accordingly
  if (args[1][0] != 'A' & args[1][0] != 'B'){
    targetA = cmdStr2Num(args[1], 10);
    targetB = cmdStr2Num(args[2], 10);
  }
  
  // in case the first argument 1 was A, only set target A
  if(args[1][0] == 'A'){
    targetA = cmdStr2Num(args[2], 10);
  }

  // in case the first argument 1 was B, only set target B
  if(args[1][0] == 'B'){
    targetB = cmdStr2Num(args[2], 10);
  }

  set_flows();
}

//>> get -> return the most recent measured flow values
void cmd_get(int arg_cnt, char **args){
  Serial.print(recentA);Serial.print(' ');Serial.println(recentB);
}

//>> open -> open the specified valve and close the rest
void cmd_open(int arg_cnt, char **args){
  int v = cmdStr2Num(args[arg_cnt-1], 10);
  if(v < 1 | v > VALVE_COUNT) return;
  for(byte i=0; i < VALVE_COUNT; i++){
    digitalWrite(valvePins[i], i==(v-1));    
  }  
}

//==== flow control subfunctions ========
void set_flows(){
  analogWrite(PWM_A, map(targetA, 0, 5000, 0, 255));
  analogWrite(PWM_B, map(targetB, 0, 5000, 0, 255));
}

void measure_flows(){
  unsigned long sumA = 0;
  unsigned long sumB = 0;
  for(int i=0; i< SAMPLES; i++){
    sumA+=analogRead(ANA_A);
    sumB+=analogRead(ANA_B);
  }
  recentA = float(sumA)/float(SAMPLES);
  recentB = float(sumB)/float(SAMPLES);
}

//=== setup and main loop================

void setup()
{ 
  // Timer1.initialize(1024);
  cmdInit(9600);
  cmdAdd("?", cmd_identify);
  cmdAdd("get", cmd_get);
  cmdAdd("set", cmd_set);
  cmdAdd("open", cmd_open);
  for(byte i=0; i < VALVE_COUNT; i++){
    pinMode(valvePins[i], OUTPUT);    
  }
  cmd_identify(0,NULL);
  set_flows();
  digitalWrite(valvePins[0],HIGH);
}

void loop() {
  measure_flows();
  cmdPoll();
}
