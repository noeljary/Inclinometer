#define CD_END_DELAY_TIME  2500

double PSI_To_BAR(double Pressure_PSI) {
   return(Pressure_PSI/PSI2BAR);
}

double PSI_To_KPA(double Pressure_PSI) {
   return(Pressure_PSI * KPA2PSI);
}

double BAR_To_PSI(double Pressure_BAR) {
   return(Pressure_BAR * PSI2BAR);
}

double KPA_To_PSI(double Pressure_KPA) {
   return(Pressure_KPA/KPA2PSI);
}

float DegC_To_DegK(float DegC) {
   return(DegC + 273.15);
}

float DegF_To_DegK(float DegF) {
   return(DegC_To_DegK(DegF_To_DegC(DegF)));
}

float DegC_To_DegF(float DegC) {
  return((DegC * 1.8) + 32.0);
}

float DegF_To_DegC(float DegF) {
   return((DegF-32.0)/1.8);
}

double ConvertPressureForDisplay(double Pressure_PSI) {
   #ifdef DISPLAY_PRESSURE_AS_BAR
      return(PSI_To_BAR(Pressure_PSI));
   #elif DISPLAY_PRESSURE_AS_KPA
      return(PSI_To_KPA(Pressure_PSI));
   #else
      return(Pressure_PSI);
   #endif
}

void EdgeInterrupt() {
  uint32_t ts = micros();
  uint32_t BitWidth;

  if(TimingsIndex == MAXTIMINGS) {
    return;
  }

  BitWidth = ts - LastEdgeTime_us;

  if(WaitingFirstEdge) {
    if(IsTooShort(BitWidth)) {
      LastEdgeTime_us = ts;  //ignore short pulses at the start of the transmission
      return;
    }

    if(digitalRead(RXPin) == LOW) {
      FirstEdgeIsHighToLow = true;
    } else {
      FirstEdgeIsHighToLow = false;
    }

    WaitingFirstEdge = false;
  }

  if(BitWidth > 0xFFFF) {
    BitWidth = 0xFFFF;
  }

  LastEdgeTime_us = ts;
  Timings[TimingsIndex++] = (uint16_t)BitWidth;
}


bool IsTooShort(uint16_t Width) {
  if(Width < SHORTTIMING_MIN) {
    return (true);
  } else {
    return (false);
  }
}

bool IsTooLong(uint16_t Width) {
  if(Width > LONGTIMING_MAX) {
    return (true);
  } else {
    return (false);
  }
}

bool IsValidSync(uint16_t Width) {
  if((Width >= SYNCTIMING_MIN) && (Width <= SYNCTIMING_MAX)) {
    return (true);
  } else {
    return (false);
  }
}

bool IsValidShort(uint16_t Width) {
  if((Width >= SHORTTIMING_MIN) && (Width <= SHORTTIMING_MAX)) {
    return (true);
  } else {
    return (false);
  }
}

bool IsValidLong(uint16_t Width) {
  if((Width >= LONGTIMING_MIN) && (Width <= LONGTIMING_MAX)) {
    return (true);
  } else {
    return (false);
  }
}

bool IsEndMarker(uint16_t Width) {
  uint16_t UpperLimit, LowerLimit;
  UpperLimit = ENDTIMING_MAX;
  LowerLimit = ENDTIMING_MIN;

  if((Width >= LowerLimit) && (Width <= UpperLimit)) {
     return(true);
  } else {
    return(false);
  }
}

int16_t ValidateBit() {
  uint16_t BitWidth = Timings[CheckIndex];

  if(IsValidLong(BitWidth)) {
    return (BITISLONG);
  }

  if(IsValidShort(BitWidth)) {
    return (BITISSHORT);
  }

  if(IsValidSync(BitWidth)) {
    return (BITISSYNC);
  }

  return (-1);
}

int16_t ValidateBit(int16_t Index) {
  uint16_t BitWidth = Timings[Index];

  if(IsValidLong(BitWidth)) {
    return (BITISLONG);
  }

  if(IsValidShort(BitWidth)) {
    return (BITISSHORT);
  }

  if(IsValidSync(BitWidth)) {
    return (BITISSYNC);
  }

  return (BITISUNDEFINED);
}

uint16_t Compute_CRC16(int16_t bcount, uint16_t Poly, uint16_t crc_init) {
  return(Compute_CRC16(0,  bcount, Poly,   crc_init ));
}

uint16_t Compute_CRC16(int16_t startbyte, int16_t bcount, uint16_t Poly, uint16_t crc_init) {
  uint16_t remainder = crc_init;
  byte Abit;

  int16_t c;
  int16_t index = startbyte;
  for(c = 0; c < bcount; c++, index++) {
    remainder ^= (( uint16_t)RXBytes[index]) << 8;
    for(Abit = 0; Abit < 8; ++Abit) {
      if(remainder & 0x8000) {
        remainder = (remainder << 1) ^ Poly;
      } else {
        remainder = (remainder << 1);
      }
    }
  }

  return remainder;
}

uint8_t Compute_CRC8(int16_t bcount, uint8_t Poly, uint8_t crc_init) {
  uint8_t crc = crc_init;
  int16_t c;

  for(c = 0; c < bcount; c++) {
    uint8_t b = RXBytes[c];
    /* XOR-in next input byte */
    uint8_t data = (uint8_t)(b ^ crc);
    /* get current CRC value = remainder */
    if(Poly == 0x07) {
      crc = (uint8_t)(pgm_read_byte(&CRC8_Poly_07_crctable2[data]));
    } else if(Poly == 0x13) {
      crc = (uint8_t)(pgm_read_byte(&CRC8_Poly_13_crctable2[data]));
    }
  }

  return crc;
}

uint8_t Compute_CRC_XOR(int16_t StartByte, int16_t bcount, uint8_t crc_init) {
  uint8_t crc = crc_init;
  int16_t index = StartByte;
  int16_t c;

  for(c = 0; c < bcount; c++,index++) {
    crc = crc ^ RXBytes[index];
  }
  
  return(crc);
}

uint8_t Compute_CRC_SUM(int16_t StartByte, int16_t bcount, uint8_t crc_init) {
  uint8_t crc = crc_init;
  int16_t c;
  int16_t index = StartByte;

  for(c = 0; c < bcount; c++,index++) {
    crc = crc + RXBytes[index];
  }
  
  return(crc);
}

int16_t GetRSSI_dbm() {
  uint8_t RSSI_Read;
  uint8_t RSSI_Offset = 74;
  int16_t ret;

  RSSI_Read = readStatusReg(CC1101_RSSI);
  if(RSSI_Read >= 128) {
    ret = (int)((int)(RSSI_Read - 256) /  2) - RSSI_Offset;
  } else {
    ret = (RSSI_Read / 2) - RSSI_Offset;
  }

  return(ret);
}

void ClearRXBuffer() {
  int16_t i;

  for(i = 0; i < (int16_t)sizeof(RXBytes); i++) {
    RXBytes[i] = 0;
  }
}

int16_t ManchesterDecode_ZeroBit(int16_t StartIndex) {
  int16_t i;
  bool bit1, bit2;
  uint8_t b = 0;
  uint8_t n = 0;

  RXByteCount = 0;
  for(i = StartIndex; i < BitCount - 1; i += 2) {
    bit1 = IncomingBits[i];
    bit2 = IncomingBits[i + 1];

    if(bit1 == bit2) {
      if(n != 0)  {
        //partial bits?
        b = b << (8 - n);
        RXBytes[RXByteCount] = b;
        RXByteCount++;            
      }

      return RXByteCount;
    }

    b = b << 1;
    b = b + (bit2 == true? 0:1);
    n++;

    if(n == 8) {
      RXBytes[RXByteCount] = b;
      RXByteCount++;
      if (RXByteCount >= (int16_t) sizeof(RXBytes)) {
        return(RXByteCount);
      }

      n = 0;
      b = 0;
    }
  }

  if(n != 0) {
    //partial bits?
    b = b << (8 - n);
    RXBytes[RXByteCount] = b;
    RXByteCount++;            
  }

  return RXByteCount;
}

int16_t ManchesterDecode(int16_t StartIndex) {
  int16_t i, index = 0;
  bool bit1, bit2;
  uint8_t b = 0;
  uint8_t n = 0;

  RXByteCount = 0;
  ManchesterBitCount = 0;
  for(i = StartIndex; i< BitCount-1;i+=2) {
    bit1 = IncomingBits[i];
    bit2 = IncomingBits[i+1];

    if(bit1 == bit2) {
      if(n != 0) {
        //partial bits?
        b = b << (8 - n);
        RXBytes[RXByteCount] = b;
        RXByteCount++;            
      }
  
      return RXByteCount;
    }

    b = b << 1;
    b = b + (bit2 == true? 1:0);
    ManchesterDecodedBits[index++] = (bit2 == true? 1:0);
    n++;

    if(n == 8) {
      RXBytes[RXByteCount] = b;
      RXByteCount++;
      if (RXByteCount >= (int16_t)sizeof(RXBytes)) {
        ManchesterBitCount = index;
        return(RXByteCount);
      }
  
      n = 0;
      b = 0;
    }
  }

  ManchesterBitCount = index;

  if(n != 0) {
    //partial bits?
     b = b << (8 - n);
     RXBytes[RXByteCount] = b;
     RXByteCount++;            
  }
 
  return RXByteCount;
}

int16_t DifferentialManchesterDecode(int16_t StartIndex) {
  int16_t i;
  bool bit1, bit2, bit3;
  uint8_t b = 0;
  uint8_t n = 0;

  RXByteCount = 0;
  for(i = StartIndex; i< BitCount-1;i+=2) {
    bit1 = IncomingBits[i];
    bit2 = IncomingBits[i+1];
    bit3 = IncomingBits[i+2];

    if (bit1 != bit2) {
      if (bit2 != bit3) {
        b = b << 1;
        b = b + 0;
        n++;
        if (n == 8) {
          RXBytes[RXByteCount] = b;
          RXByteCount++;
          n = 0;
          b = 0;
        }          
      } else {
        bit2 = bit1;
        i+=1;
        break;
      }
    } else {
      bit2 = 1 - bit1;
      break;
    }
  }

  for(; i< BitCount-1;i+=2) {
    bit1 = IncomingBits[i];

    if (bit1 == bit2) {
      return RXByteCount;
    }

    bit2 = IncomingBits[i+1];

    b = b << 1;
    b = b + (bit1 == bit2? 1:0);
    n++;

    if(n == 8) {
      RXBytes[RXByteCount] = b;
      RXByteCount++;
      n = 0;
      b = 0;
    } 
  }

  return RXByteCount;
}

void InvertBitBuffer() {
   int16_t i;

   for(i = 0;i < BitCount;i++) {
      IncomingBits[i] = !IncomingBits[i];
   }
}

static inline uint8_t bit_at(const uint8_t *bytes, uint16_t bit) {
  return (uint8_t)(bytes[bit >> 3] >> (7 - (bit & 7)) & 1);
}

int16_t FindManchesterStart(const uint8_t *pattern, int16_t pattern_bits_len) {
   int16_t ipos = 0;
   int16_t ppos = 0; // cursor on init pattern

  if(BitCount < pattern_bits_len) {
    return -1;
  }  

  while((ipos < BitCount-3) && (ppos < pattern_bits_len)) {
    if(IncomingBits[ipos] == bit_at(pattern, ppos)) {
      ppos++;
      ipos++;
      if (ppos == pattern_bits_len) {
        return ipos;
      }
    } else  {
      ipos -= ppos;
      ipos++;
      ppos = 0;
    }
  }

  // Not found
  return -1; 
}

void InitDataBuffer() {
  BitIndex = 0;
  BitCount = 0;
  ValidBlock = false;
  WaitingFirstEdge  = true;
  CheckIndex = 0;
  TimingsIndex = 0;
  SyncFound = false;
}

void PulseDebugPin(int16_t width_us) {
  digitalWrite(DEBUGPIN, HIGH);
  delayMicroseconds(width_us);
  digitalWrite(DEBUGPIN, LOW);
}

void UpdateFreqOffset() {
  FreqOffsetAcc = FreqOffsetAcc + readStatusReg(CC1101_FREQEST);
  writeReg(CC1101_FSCTRL0, FreqOffsetAcc);
}

void PrintTimings(uint8_t StartPoint, uint16_t Count) {
  char c[10];

  for(uint16_t i = 0; i < Count; i++) {
    if((StartPoint == 0) && (i == (uint16_t)StartDataIndex)) {
       Serial.println();
    }

    sprintf(c, "%3d,",Timings[StartPoint + i]);
    Serial.print(c);
  }

  Serial.println(F(""));
}

void PrintManchesterData(int16_t StartPos, uint16_t Count, bool ShowHex) {
  uint8_t hexdata = 0;

  for(uint16_t i = StartPos, c = 1; c <= Count; i++, c++) {
    Serial.print(ManchesterDecodedBits[i]);
    if(ShowHex) {
      hexdata = (hexdata << 1) + ManchesterDecodedBits[i];
      if (c % 8 == 0) {
        Serial.print(F(" ["));
        Serial.print(hexdata, HEX);
        Serial.print(F("] "));
        hexdata = 0;
      }
    }
  }

  Serial.println(F("")); 
}

void PrintData(int16_t StartPos, uint16_t Count, bool ShowHex) {
  uint8_t hexdata = 0;

  for(uint16_t i = StartPos, c = 1; c <= Count; i++, c++) {
    Serial.print(IncomingBits[i]);
    if(ShowHex) {
      hexdata = (hexdata << 1) + IncomingBits[i];
      if (c % 8 == 0) {
        Serial.print(F(" ["));
        Serial.print(hexdata, HEX);
        Serial.print(F("] "));
        hexdata = 0;
      }
    }
  }

  Serial.println(F(""));
}

void PrintData(int16_t StartPos, uint16_t Count) {
  PrintData(StartPos, Count, true);
}

void PrintData(uint16_t Count) {
  PrintData(0, Count, true);
}

void PrintBytes(uint16_t Count) {
  for (uint16_t i = 0; i < Count; i++) {
    Serial.print(F(" ["));
    Serial.print(RXBytes[i],HEX);
    Serial.print(F("] "));
  }

  Serial.println(F(""));
}

void DisplayStatusInfo() {
  Serial.print(F("FreqOffset: "));
  Serial.print(FreqOffset);
  Serial.print(F("  DemodLinkQuality: "));
  Serial.print(DemodLinkQuality);
  Serial.print(F("  RSSI: "));
  Serial.println(RSSIvalue);
}

int16_t DecodeBitArray(int16_t StartIndex, uint8_t ShiftRightBitCount) {
  //convert 1s and 0s array to byte array
  int16_t n = 0;
  uint8_t b = 0;

  ClearRXBuffer();

  n = ShiftRightBitCount;  //pad with this number of 0s to the left
  RXByteCount = 0;

  for(int16_t i = StartIndex; i < BitCount; i++) {
    b = b << 1;
    b = b + IncomingBits[i];
    n++;

    if(n == 8) {
      RXBytes[RXByteCount] = b;
      RXByteCount++;
      n = 0;
      b = 0;
    }
  }

  return (RXByteCount);
}

int16_t DecodeBitArray(uint8_t ShiftRightBitCount) {
  //convert 1s and 0s array to byte array
  int16_t n = 0;
  uint8_t b = 0;

  ClearRXBuffer();

  n = ShiftRightBitCount;  //pad with this number of 0s to the left
  RXByteCount = 0;
  
  for(int16_t i = 0; i < BitCount; i++) {
    b = b << 1;
    b = b + IncomingBits[i];
    n++;

    if(n == 8) {
      RXBytes[RXByteCount] = b;
      //Serial.print(RXBytes[RXByteCount],HEX);
      //Serial.print(" - ");
      RXByteCount++;
      n = 0;
      b = 0;
    }
  }

  return (RXByteCount);
}

bool ReceiveMessage() {
  bool ValidMessage = false;
  bool EarlyExit = false;

  int16_t lRSSI = 0;
  uint32_t t1;

  uint32_t CD_Start;
  uint32_t TimeSinceLastEdge;
  uint32_t CD_Timing;

  //set up timing of edges using interrupts...
  LastEdgeTime_us = micros();
  CD_Start = LastEdgeTime_us;

  attachInterrupt(digitalPinToInterrupt(RXPin), EdgeInterrupt, CHANGE);

  #ifdef ARDUINO_SEEED_XIAO_M0
  NVIC_SetPriority(EIC_IRQn, 2);  //!!!!! this is necessary for the Seeeduino Xiao due external interupts having a higher priority than the micros() timer rollover (by default). 
                                  // This can cause the micros() value to appear to go 'backwards' in time in the external interrupt handler and end up giving an incorrect 65536 bit width result.
  #elif ARDUINO_SEEED_XIAO_RP2040
  //NVIC_SetPriority(EIC_IRQn, 2);
  #endif

  RSSIvalue = -1000;

  while(GetCarrierStatus() == true) {
     //get the maximum RSSI value seen during data receive window
     lRSSI = GetRSSI_dbm();
     if (lRSSI > RSSIvalue) {
       RSSIvalue = lRSSI;
     }

     noInterrupts();
     t1 = micros();
     TimeSinceLastEdge = t1 - LastEdgeTime_us;
     CD_Timing = t1 - CD_Start;
     interrupts();

     if(((CD_Timing) > CDWIDTH_MAX) || ((TimingsIndex > EXPECTEDBITCOUNT) && (TimeSinceLastEdge > ENDTIMING_MAX) && (ENDTIMING_MAX > 0))) {
        EarlyExit = true;
        break;
     }
  }

  delayMicroseconds(CD_END_DELAY_TIME);  //there is a delay on the serial data stream so ensure we allow a bit of extra time after CD finishes to ensure all the data is captured
  detachInterrupt(digitalPinToInterrupt(RXPin)); 
  EdgeInterrupt();  //force a final edge change just to be sure
  CD_Width = micros() - CD_Start;
  CD_Width = CD_Width - CD_END_DELAY_TIME;
  setIdleState();  //force carrier sense to end

  if(((CD_Width >= CDWIDTH_MIN) && (CD_Width <= CDWIDTH_MAX) && (TimingsIndex > EXPECTEDBITCOUNT )) || ((EarlyExit == true) && (TimingsIndex > EXPECTEDBITCOUNT))) {
    #ifdef SHOWDEBUGINFO
    Serial.println(F("******************************************************************"));
    Serial.println(F("Checking...."));
    #endif
    CheckIndex = 0;
    ValidMessage = ValidateTimings();
    
    #ifdef SHOWDEBUGINFO
    Serial.println(F("Timings...."));
    Serial.print(F("CD_Width="));
    Serial.println(CD_Width);
    Serial.print(F("TimingsIndex="));
    Serial.println(TimingsIndex);
    Serial.print(F("Checking complete. Bitcount: "));
    Serial.print(BitCount);
    Serial.print(F("  StartDataIndex: "));
    Serial.println(StartDataIndex);
    Serial.print(F(" RSSI(dBm):"));
    Serial.println(RSSIvalue);
    #ifdef ALWAYSSHOWTIMINGS
    PrintTimings(0,TimingsIndex+1);
    PrintData(BitCount);
    PrintBytes(EXPECTEDBYTECOUNT);
    #else
    if(ValidMessage) {
      PrintTimings(0,TimingsIndex+1);
      PrintData(BitCount);
      PrintBytes(EXPECTEDBYTECOUNT);
    }       
    #endif
    #endif

    Flush_RX_FIFO(true);
    return (ValidMessage);
  } else {
    #ifdef SHOWDEBUGINFO
    if(TimingsIndex >= 50) {
      Serial.println(F("******************************************************************"));
      Serial.print(F("CD_Width*="));
      Serial.println(CD_Width);   
      Serial.print(F("TimingsIndex="));
      Serial.println(TimingsIndex); 
      PrintTimings(0,TimingsIndex+1);  
      PrintData(BitCount);
    }
    #endif
   
    Flush_RX_FIFO(true);
    return (false);
  }
}
