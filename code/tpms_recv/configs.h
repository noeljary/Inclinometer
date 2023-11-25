//Receive frequency
#define UK_433MHz 1
//#define US_315MHz 1

//Vehicle/sensor type
//#define Toyota_TRW_C070 1
#define Toyota_PMV_C210 1   //Toyota Auris, should also work for PMV-C010?? and PMV-C215 (Toyota Corolla)
//#define Hyundai_i35 1  //uses PMV-C210 sensor
//#define Schrader_C1100 1  //used on Hyundai Tucson TL/TLE 01/2015-12/2015
//#define Schrader_A9054100 1
//#define Toyota_PMV_107J 1   //used on Lexus RX series 07/2013-09/2015
//#define Renault 1
//#define Zoe 1   //for Renault Zoe 09/2012 to 06/2019 only (you must select 'Renault' define as well for this!)
//#define Dacia 1
//#define NissanLeaf 1
//#define Citroen 1
//#define PontiacG82009 1
//#define TruckSolar 1
//#define JansiteSolar 1 
//#define Subaru 1
//define Ford 1

#ifdef Ford_FSeries_SD
   #define FordType 2
#elif Ford_FSeries_2006_2008
   #define FordType 1
#elif Ford_ESeries_TEST
   #define FordType 3
#else
   #define FordType 0
#endif

int Ford_SensorType = FordType;  //3 different types seen, select 0,1,2 to match the pressure readings


//config checks...
#if defined(UK_433MHz) && defined(US_315MHz)
   #error Cannot define both 433MHz and 315MHz simultaneously
#endif

#if !defined(UK_433MHz) && !defined(US_315MHz)
   #error Must define either 433MHz or 315MHz
#endif



