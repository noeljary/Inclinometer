from machine import Pin
import time

# I2C ADDRESS
_CST816_ADDR = const(0x15)

# Register Addresses
_CST816_GestureID = const(0x01)
_CST816_FingerNum = const(0x02)
_CST816_XposH = const(0x03)
_CST816_XposL = const(0x04)
_CST816_YposH = const(0x05)
_CST816_YposL = const(0x06)

_CST816_ChipID = const(0xA7)
_CST816_ProjID = const(0xA8)
_CST816_FwVersion = const(0xA9)
_CST816_MotionMask = const(0xAA)

_CST816_BPC0H = const(0xB0)
_CST816_BPC0L = const(0xB1)
_CST816_BPC1H = const(0xB2)
_CST816_BPC1L = const(0xB3)

_CST816_IrqPluseWidth = const(0xED)
_CST816_NorScanPer = const(0xEE)
_CST816_MotionSlAngle = const(0xEF)
_CST816_LpScanRaw1H = const(0xF0)
_CST816_LpScanRaw1L = const(0xF1)
_CST816_LpScanRaw2H = const(0xF2)
_CST816_LpScanRaw2L = const(0xF3)
_CST816_LpAutoWakeTime = const(0xF4)
_CST816_LpScanTH = const(0xF5)
_CST816_LpScanWin = const(0xF6)
_CST816_LpScanFreq = const(0xF7)
_CST816_LpScanIdac = const(0xF8)
_CST816_AutoSleepTime = const(0xF9)
_CST816_IrqCtl = const(0xFA)
_CST816_AutoReset = const(0xFB)
_CST816_LongPressTime = const(0xFC)
_CST816_IOCtl = const(0xFD)
_CST816_DisAutoSleep = const(0xFE)

# Modes
_CST816_Point_Mode = const(1)
_CST816_Gesture_Mode = const(2)
_CST816_ALL_Mode = const(3)

# Gestures
CST816_Gesture_None = const(0)
CST816_Gesture_Up = const(1)
CST816_Gesture_Down = const(2)
CST816_Gesture_Left = const(3)
CST816_Gesture_Right = const(4)
CST816_Gesture_Click = const(5)
CST816_Gesture_Double_Click = const(11)
CST816_Gesture_Long_Press = const(12)

class CST816:

    def __init__(self, i2c, mode, rstPin, intPin):
        self._i2c = i2c

        self.x_point = 0
        self.y_point = 0
        self.event = 0
        self.points = 0
        self.gestures = 0
        
        self.triggered = False

        self.rst = Pin(rstPin, Pin.OUT)
        self.int = Pin(intPin,Pin.IN, Pin.PULL_UP)
        
        self.reset()
        
        if self.who_am_i():
            self.stop_sleep()
            self.mode = mode
            self.set_mode(mode)
            self.int.irq(handler=self.int_callback, trigger=Pin.IRQ_FALLING)
        else:
            print("Unable to Initialise Device")


    def _read_byte(self,cmd):
        rec = self._i2c.readfrom_mem(int(_CST816_ADDR), int(cmd),1)
        return rec[0]


    def _read_block(self, reg, length=1):
        rec = self._i2c.readfrom_mem(int(_CST816_ADDR), int(reg), length)
        return rec


    def _write_byte(self, cmd, val):
        self._i2c.writeto_mem(int(_CST816_ADDR), int(cmd), bytes([int(val)]))


    def who_am_i(self):
        return self._read_byte(0xA7) == (0xB5)


    def reset(self):
        self.rst(0)
        time.sleep_ms(1)
        self.rst(1)
        time.sleep_ms(50)


    def read_revision(self):
        return self._read_byte(_CST816_FwVersion)


    def wake_up(self):
        self.i2c.writeto_mem(_CST816_ADDR, _CST816_DisAutoSleep, bytes([0x00]))
        time.sleep(0.01)
        self.i2c.writeto_mem(_CST816_ADDR, _CST816_DisAutoSleep, bytes([0x01]))
        time.sleep(0.05)
        self.i2c.writeto_mem(_CST816_ADDR, _CST816_DisAutoSleep, bytes([0x01]))


    def stop_sleep(self):
        self._write_byte(_CST816_DisAutoSleep, 0x01)


    def set_mode(self, mode):
        if (mode == _CST816_Point_Mode): # Point Mode
            self._write_byte(_CST816_IrqCtl, 0X41)
        elif (mode == _CST816_Gesture_Mode): # Gesture Mode
            self._write_byte(_CST816_IrqCtl, 0X71)
        else: # Mixed Mode
            self._write_byte(_CST816_IrqCtl, 0X11)
            self._write_byte(0xEC, 0X01)

        self.mode = mode


    def get_point(self):
        touch = self._read_block(0x01, 6)
        
        self.gesture = touch[0]
        self.event = touch[2] >> 6
        
        if self.event == 1 and self.gesture > 0:
            self.points = touch[1]
            self.x_point = ((touch[2] & 0x0f) << 8) + touch[3]
            self.y_point = ((touch[4] & 0x0f) << 8) + touch[5]
            return (True, (self.gesture, (self.x_point, self.y_point)))
        
        return (False,)

    def get_gesture(self):
        self.gesture = self._read_byte(_CST816_GestureID)


    def get_touch(self):
        self.fingers = self._read_byte(_CST816_FingerNum)


    def int_callback(self, pin):
        self.triggered = True


    def read_trigger(self):
        if self.triggered:
            self.triggered = False
            return(self.get_point())
        else:
            return (False,)
