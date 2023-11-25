#define VERSION "11.8"

#include <SPI.h>
#include "configs.h"
#include "globals.h"
#include "CommonFunctionDeclarations.h"

#ifdef Toyota_PMV_C210
   #include "Toyota_PMV_C210.h"
#elif Toyota_PMV_107J
   #include "Toyota_PMV_107J.h"
#elif defined(Toyota_TRW_C070) || defined(Hyundai_i35)
   #include "Toyota_TRW_C070.h"
#elif defined Schrader_C1100
   #include "Schrader_C1100.h"
#elif defined Schrader_A9054100
   #include "Schrader_A9054100.h"
#elif NissanLeaf
   #include "Renault.h"
#elif Dacia
   #include "Renault.h"
#elif  Renault
   #include "Renault.h"
#elif Citroen
   #include "Citroen.h"
#elif Ford
   #include "Ford.h"
#elif  Jansite
   #include "Jansite.h"
#elif  JansiteSolar
   #include "JansiteSolar.h"
#elif PontiacG82009
   #include "PontiacG82009.h"
#elif TruckSolar
   #include "TruckSolar.h"
#elif Subaru
   #include "Subaru.h"
#endif

#include "cc1101.h"
#include "Common.h"

void setup() {
  uint8_t resp;
  uint8_t regfail;

  //SPI CC1101 chip select set up
  pinMode(CC1101_CS, OUTPUT);
  digitalWrite(CC1101_CS, HIGH);

  // Init USB Serial
  Serial.begin(115200);

  pinMode(LED_RX, OUTPUT);
  pinMode(RXPin, INPUT);
  pinMode(CDPin, INPUT);

  delay(2000);
  SPI.begin();
	delay(2000);

  Serial.println(F("########################################################################"));
  Serial.println(F("STARTING..."));
  Serial.print(F("Software version "));
  Serial.println(VERSION);
  Serial.print(F("Configured for processor type "));
  Serial.println(PROC_TYPE);

  //initialise the CC1101
  Serial.print(F("Resetting CC1101 "));
  uint8_t retrycount = 0;
  while(retrycount < 5) {
    Serial.print(F("."));
    CC1101_reset();
    if(readConfigReg(0) == 0x29) {
      break;
    }
    retrycount++;
    delay(5);
  }
  Serial.println(F(""));

  if(readConfigReg(0) == 0x29) {
    Serial.println(F("CC1101 reset successful"));
  } else {
    Serial.println(F("CC1101 reset failed. Try rebooting")); 
  }

  ConfigureCC1101();
  Serial.print(F("CC1101 configured for "));
  #ifdef US_315MHz
  Serial.print (F("US (315MHz)"));
  #else
  Serial.print (F("UK (433MHz)"));
  #endif

  #ifdef Toyota_PMV_C210
  Serial.println (F(" and PMV-C210 TPMS sensor"));
  #elif Ford
  Serial.println (F(" and Ford TPMS sensor"));
  #endif

  setIdleState();
  digitalWrite(LED_RX, HIGH);

  resp = readStatusReg(CC1101_PARTNUM);
  Serial.print(F("CC1101 Part no: "));
  Serial.println(resp, HEX);

  resp = readStatusReg(CC1101_VERSION);
  Serial.print(F("CC1101 Version: "));
  Serial.println(resp, HEX);

  regfail = VerifyCC1101Config();
  if(regfail > 0) {
     Serial.print(F("Config verification fail #"));
     Serial.println(regfail);
  } else {
     Serial.println(F("Config verification OK"));
  }

  digitalWrite(LED_RX, LOW);

  pinMode(DEBUGPIN, OUTPUT);
  digitalWrite(DEBUGPIN, LOW);

  digitalWrite(LED_RX, HIGH);


  //Calibrate();
  LastCalTime = millis();
  
  setRxState();
  Flush_RX_FIFO(true);
}

void loop() {
  if(millis() - LastCalTime > CAL_PERIOD_MS) {
    setIdleState();  //configuration is set to auto-cal when goimg from Idle to RX
    LastCalTime = millis();
    setRxState();      
  }

  InitDataBuffer();

  //wait for carrier status to go low
  while(GetCarrierStatus() == true) {}

  //wait for carrier status to go high  looking for rising edge
  while(GetCarrierStatus() == false) {
    if (Get_RX_FIFO_Count() > 0) {
      Flush_RX_FIFO(true);
    }
    delay(1);
  }

  if(GetCarrierStatus() == true) { 
    //looks like some data coming in...
    if(ReceiveMessage()) {
      DecodeTPMS();
    }
  }
}
