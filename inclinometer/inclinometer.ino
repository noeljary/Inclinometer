#include <EEPROM.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BNO055.h>

#define AVG_SIZE 10

Adafruit_BNO055 bno = Adafruit_BNO055(55, 0x28);

bool store_calibration = false;
byte loop_iter = 0;
float rolling_x[AVG_SIZE], rolling_y[AVG_SIZE], rolling_z[AVG_SIZE];

void setup() {
  // Begin Serial Connection for Debug
  Serial.begin(115200);

  // Verify BNO055 Attached and Functional
  if (!bno.begin()) {
    Serial.println("No BNO055 Detected!");
    while(1);
  }

  // Initialise Rolling Average Array
  for(byte i = 0; i > AVG_SIZE; i++) {
    rolling_x[i] = 0;
    rolling_y[i] = 0;
    rolling_z[i] = 0;
  }

  // Wait for BNO055 to Boot
  delay(1000);

  // Attempt to Load Calibration from EEPROM
  if(!loadCalibration()) {
    // Run Calibration Routines if Not Pre-Calibrated
    adafruit_bno055_offsets_t calData = doCalibration();
    storeCalibration(calData);
  }

  // Use External Crystal
  bno.setExtCrystalUse(true);
}

bool loadCalibration() {
  // Calibration Routines
  long bnoID;
  int eeAddr = 0;
  adafruit_bno055_offsets_t calData;
  sensor_t sensor;

  // Lookup BNO055 ID
  EEPROM.get(eeAddr, bnoID);
  bno.getSensor(&sensor);

  // Check if Calibration Data in EEPROM
  if(bnoID != sensor.sensor_id) {
    Serial.println("No Calibration Data Stored in EEPROM");
  } else {
    // Found Calibration Data and Load Into BNO055
    Serial.println("Found Calibration Data Stored in EEPROM");
    EEPROM.get(eeAddr + sizeof(long), calData);
    bno.setSensorOffsets(calData);
    return true;
  }

  return false;
}

adafruit_bno055_offsets_t doCalibration() {
  Serial.println("Running Calibration Routine");
  while(!bno.isFullyCalibrated()) {
    // Get Calibration Scores
    displayCalibration();
    delay(100);
  }

  // Now Calibrated - Get Offsets to be Soted
  adafruit_bno055_offsets_t calData;
  bno.getSensorOffsets(calData);
  return calData;
}

void displayCalibration() {
  // Get Calibration Scores
  uint8_t cal[4];
  bno.getCalibration(&cal[0], &cal[1], &cal[2], &cal[3]);

  Serial.print("System Calibration: ");
  Serial.print(cal[0]);
  Serial.print(" Gyro: ");
  Serial.print(cal[1]);
  Serial.print(" Accelerometer: ");
  Serial.print(cal[2]);
  Serial.print(" Magnetometer: ");
  Serial.println(cal[3]);
}

bool isCalibrated() {
  // Get Calibration Scores
  uint8_t cal[4];
  bno.getCalibration(&cal[0], &cal[1], &cal[2], &cal[3]);

  // Check Calibration Scores are Sufficient
  for(byte i = 1; i < 4; i++) {
    if(cal[i] < 3) {
      return false;
    }
  }
  
  return true;
}

void storeCalibration(adafruit_bno055_offsets_t calData) {
  int eeAddress = 0;
  sensor_t sensor;
  bno.getSensor(&sensor);
  long bnoID = sensor.sensor_id;

  // Store Calibration Data in EEPROM
  EEPROM.put(eeAddress, bnoID);
  EEPROM.put(eeAddress + sizeof(long), calData);
  Serial.println("Calibration Data Stored in EEPROM");
}

void displayOrientation(float x, float y, float z) {
  Serial.print("Compass: ");
  Serial.print(x);
  Serial.print(" Roll: ");
  Serial.print(y);
  Serial.print(" Pitch: ");
  Serial.println(z);
}

void loop() {
  // Get Orientation Data if Calibrated
  if(isCalibrated()) {
    // Get Absolute Orientataion Data
    sensors_event_t orientation;
    bno.getEvent(&orientation, Adafruit_BNO055::VECTOR_EULER);

    // Fill Rolling Average Array
    rolling_x[loop_iter] = orientation.orientation.x;
    rolling_y[loop_iter] = orientation.orientation.y;
    rolling_z[loop_iter] = orientation.orientation.z;

    // Calculate Rolling Average Value
    float x = 0, y = 0, z = 0;
    for(byte i = 0; i < AVG_SIZE; i++) {
      x += rolling_x[i];
      y += rolling_y[i];
      z += rolling_z[i];
    }

    x /= AVG_SIZE;
    y /= AVG_SIZE;
    z /= AVG_SIZE;

    loop_iter = (loop_iter == AVG_SIZE - 1) ? 0 : loop_iter + 1;

    // Show Orientation
    displayOrientation(x, y, z);
  } else {
    // Show Calibration Scores until Sufficient
    displayCalibration();
  }

  delay(50);
}
