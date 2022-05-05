#include "src/CmdArduino//Cmd.h"
#include <Servo.h>

#define DEVICE "IsWISaS_Controller"
#define MODEL "C"
#define VERSION "0.1_pump&Servo"

#define VALVE_UPDATE_INTERVAL 1000
unsigned int latestValveUpdate;

#define PIN_SERVO_POSITION A5
#define PIN_SERVO_ENABLE 9
#define POS_A 20
#define POS_B 125
#define POS_X 75

/*-----( Declare objects )-----*/
Servo myservo;  // create servo object to control a servo
char servoPos = 'A';
/*-----------------------------------------*/

struct valveSlotType{
  byte box;
  byte slot;  
};

//------- valve control stuff ----------------
#define VALVE_COUNT 7
int valvePins[VALVE_COUNT] = {8, 7, 10, 11, 4, 3, 2};

valveSlotType primaryValve   = {1,0};
valveSlotType secondaryValve = {1,0};

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
        digitalWrite(valvePins[i], ((primaryValve.box==0)   & (i == primaryValve.slot-1)) |
                                   ((secondaryValve.box==0) & (i == secondaryValve.slot-1)));
  }

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

void set_servo(byte pos){
  digitalWrite(PIN_SERVO_ENABLE, HIGH);
  myservo.write(pos);
  delay(500);
  digitalWrite(PIN_SERVO_ENABLE, LOW); 
}

void cmd_servo(int arg_cnt, char **args){

  if(arg_cnt<2){
    if(servoPos=='A'){
      set_servo(POS_B);
      servoPos = 'B';
    }else{
      set_servo(POS_A);
      servoPos = 'A';
    }    
    return;
  }

  Serial.println(args[1][0]);

  if(args[1][0] == 'A' | args[1][0] == 'B' | args[1][0] == 'X'){
    if(args[1][0] == 'A') set_servo(POS_A);
    if(args[1][0] == 'B') set_servo(POS_B);
    if(args[1][0] == 'X') set_servo(POS_X);
    servoPos = args[1][0];
    return;
  }
  set_servo(atoi(args[1]));
  servoPos = '?';
}

//......................................

void cmd_valve(int arg_cnt, char **args){

  // in case no second argument was passed, just print the active valve
  if(arg_cnt < 2){
    get_activeValve();
    return;
  }
  primaryValve = parse_valveSlot(args[1]);
  
  if(arg_cnt >2)
    secondaryValve = parse_valveSlot(args[2]);
  
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
  cmdAdd("s", cmd_servo);

  for(byte i = 0; i<VALVE_COUNT; i++){
    pinMode(valvePins[i], OUTPUT);
    digitalWrite(valvePins[i], LOW);
  }

  pinMode(PIN_SERVO_ENABLE, OUTPUT);
  digitalWrite(PIN_SERVO_ENABLE, LOW);
  
  update_valves();

  myservo.attach(PIN_SERVO_POSITION);
  set_servo(POS_A);
  
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
