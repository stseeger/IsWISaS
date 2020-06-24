//#include "src/TimerOne/TimerOne.h"
#include "src/CmdArduino/Cmd.h"


#define DEVICE "IsWISaS_Controller"
#define MODEL "A"
#define VERSION "1.0"

// PWM pins for the RC-circuits
#define PWM_A 5
#define PWM_B 6

// analog pins for reading the flow controllers' feedback
#define ANA_A A5
#define ANA_B A6


// pins to control the valves
#define VALVE_COUNT 16
const int valvePins[16] = { 9,  8,  7,  10,  11,  4,  3,  2,
                            A0, A1, A2,  A3,  A4, A5, 12, 13};

byte activeValve = 1;

// varaibles to save target flow values and actual flow rates
float recentA = 0;
float recentB = 0;

float targetA = 0;
float targetB = 0;
                                                        
#define SAMPLES 100 // number of samples for flow rate measurements

//=== serial communication ===========

void cmd_identify(int arg_cnt, char **args){
  Serial.print(DEVICE);
  Serial.print(" ");
  Serial.print(MODEL);
  Serial.print(" ");
  Serial.println(VERSION);  
}

void cmd_flow(int arg_cnt, char **args){

  if(arg_cnt == 1){
    measure_flows();
     Serial.print(recentA);Serial.print(' ');Serial.println(recentB);
     return;
  }

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

//==== flow control subfunctions ========
void set_flows(){
  analogWrite(PWM_A, map(targetA, 0, 5000, 0, 255));
  analogWrite(PWM_B, map(targetB, 0, 5000, 0, 255));

  //Timer1.pwm(PWM_A, map(targetA, 0, 5000, 0, 1023));
  //Timer1.pwm(PWM_B, map(targetB, 0, 5000, 0, 1023));
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
  //Timer1.initialize(100); // 100 µs -> 10 kHz
  cmdInit(9600);
  cmdAdd("?", cmd_identify);  
  //cmdAdd("flow", cmd_flow);
  cmdAdd("valve", cmd_valve);
  for(byte i=0; i < VALVE_COUNT; i++){
    pinMode(valvePins[i], OUTPUT);    
    digitalWrite(valvePins[i], i == (activeValve-1));
  }  
  cmd_identify(0,NULL);
  for(byte i=0; i<30; i++)Serial.print('=');
  Serial.print("\n>> ");
  set_flows();    
}

void loop() { 
  cmdPoll();
}
