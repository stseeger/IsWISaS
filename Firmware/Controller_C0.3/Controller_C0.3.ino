#include "src/CmdArduino//Cmd.h"
#include <SoftwareSerial.h>

#define DEVICE "IsWISaS_Controller"
#define MODEL "C"
#define VERSION "0.3"

#define VALVE_UPDATE_INTERVAL 1000
unsigned int latestValveUpdate;

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

//------- valve control stuff ----------------
#define VALVE_COUNT 7
//#define BOX0_FLUSH_VALVE 2 // will be opened, when secondaryValve != 0#0
int valvePins[VALVE_COUNT] = {9, 8, 7, 10, 11, 4, 3, 2};

valveSlotType primaryValve   = {1,1};
valveSlotType secondaryValve = {0,0};
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

  //digitalWrite(BOX0_FLUSH_VALVE, secondaryValve.slot>0);

  digitalWrite(portOne_EN, HIGH);
  delay(50);
  portOne.print("valve ");
  portOne.print(primaryValve.box);
  portOne.print('#');
  portOne.print(primaryValve.slot);
  portOne.print(' ');
  portOne.print(secondaryValve.box);
  portOne.print('#');
  portOne.print(secondaryValve.slot);
  portOne.print("\r\n");
  portOne.flush();
  digitalWrite(portOne_EN, LOW);

  digitalWrite(portTwo_EN, HIGH);
  delay(50);
  portTwo.print("valve ");
  portTwo.print(primaryValve.box);
  portTwo.print('#');
  portTwo.print(primaryValve.slot);
  portTwo.print(' ');
  portTwo.print(secondaryValve.box);
  portTwo.print('#');
  portTwo.print(secondaryValve.slot);
  portTwo.print("\r\n");
  portTwo.flush();
  digitalWrite(portTwo_EN, LOW);

  latestValveUpdate = millis();  
}

//.........................................
void get_activeValve(){
  Serial.print("valve>");
  Serial.print(primaryValve.box);
  Serial.print('#');
  Serial.print(primaryValve.slot);
  
  Serial.print(' ');
  Serial.print(secondaryValve.box);
  Serial.print('#');
  Serial.print(secondaryValve.slot);

  //Serial.print(' ');
  //Serial.print(groupValve.box);
  //Serial.print('#');
  //Serial.print(groupValve.slot);
  
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

//==========================================

void cmd_identify(int arg_cnt, char **args){
  Serial.print(DEVICE);
  Serial.print(' ');
  Serial.print(MODEL);
  Serial.print(' ');
  Serial.println(VERSION);  
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
    secondaryValve = parse_valveSlot(args[2]);

  if(arg_cnt > 3)
    groupValve = parse_valveSlot(args[3]);
  
  update_valves();  
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
}

//------------------------------

void loop() {
  cmdPoll();
  
  // regularly update the valves in case any extension has missed something
  /*if((millis() - latestValveUpdate) > VALVE_UPDATE_INTERVAL){
    update_valves();
  }*/
}
