
#define LED_PIN_PATTERN 10
#define LED_PIN_ERROR 11
#define LED_PIN_UNITY 12

byte ledPins[3] = {LED_PIN_PATTERN, LED_PIN_UNITY, LED_PIN_ERROR};

byte anaPins[8] = {A0,A4,A1,A2,A3,A5,A6,A7};
byte digPins[8] = {2,6,3,4,5,7,8,9};

byte pattern[8][8] = {{1,0,0,0,0,0,0,0},
                      {0,1,0,0,0,0,0,0},
                      {0,0,1,1,1,0,0,0},
                      {0,0,1,1,1,0,0,0},
                      {0,0,1,1,1,0,0,0},
                      {0,0,0,0,0,1,1,1},
                      {0,0,0,0,0,1,1,1},
                      {0,0,0,0,0,1,1,1}};
void setup() {
  Serial.begin(9600);

  for(byte i=0;i<3;i++){    
    pinMode(ledPins[i], OUTPUT);
    digitalWrite(ledPins[i], LOW);
  }
  
  for(byte i=0;i<8;i++){
      pinMode(anaPins[i], INPUT_PULLUP);
      pinMode(digPins[i], INPUT);
      digitalWrite(digPins[i],HIGH);
  }
}

void loop() {

  boolean patternMatch = 1;
  boolean unityMatch = 1;
  boolean freeFloating = 1;
  boolean Error = 0;
  
  for(byte n=0;n<8;n++){
    pinMode(digPins[n],OUTPUT);
    digitalWrite(digPins[n],LOW);
    for(byte i=0;i<8;i++){
       //if(i>0) Serial.print(" ");
       int val = analogRead(anaPins[i]);
       bool isConnected = (1023-val)>990;
       patternMatch = patternMatch & pattern[n][i] == isConnected;
       unityMatch = unityMatch & (n==i)==isConnected;
       freeFloating = freeFloating & !isConnected;
       //Serial.print(isConnected);
       delay(5);
    }
    //Serial.println("");
    digitalWrite(digPins[n],HIGH);
    pinMode(digPins[n],INPUT);    
  }
  //Serial.println("----------------");
  if(patternMatch | unityMatch | freeFloating){
    //if(patternMatch) Serial.println("Pattern matched!");
    //if(unityMatch)   Serial.println("Unity matched!"); 
    //if(freeFloating) Serial.println("Floating free!");
    byte a=1;    
  }else{
    Error=1;
    //Serial.println("Something is wrong!");
  }
  //Serial.println("================");

  for(byte i=0;i<3;i++){    
    digitalWrite(ledPins[i], LOW);
  }

  if(patternMatch) digitalWrite(LED_PIN_PATTERN,HIGH);
  if(unityMatch) digitalWrite(LED_PIN_UNITY,HIGH);
  if(Error) digitalWrite(LED_PIN_ERROR,HIGH);
  
  delay(100);
}
