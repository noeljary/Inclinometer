import board, math, time
import displayio, busio, terminalio
import gc9a01
import adafruit_bno055
import adafruit_bmp280

from adafruit_display_shapes.Circle import Circle
from adafruit_display_shapes.Rect   import Rect
from adafruit_display_shapes.Line   import Line
from adafruit_display_text          import label
from adafruit_display_text          import bitmap_label
from adafruit_bitmap_font           import bitmap_font


# Initialised Variables
conf_map = {"COMPASS" : True, "COMPASS_DEG" : True, "CARDINALS" : True, "PRESSURE" : True, "TEMPERATURE" : True, "UART_LVL" : True}
spi_int  = {"CLK" : board.GP6, "MOSI" : board.GP7, "DC" : board.GP10, "CS" : board.GP9, "RST" : board.GP11, "BLK" : board.GP12}
col_map  = [(15, 0x69B34C), (50, 0xFF8E15), (90, 0xFF0D0D)]

disp      = {}
fonts     = {}
cps_elems = {}

uart   = None
i2c    = None
bno055 = None
bmp280 = None

# Movement Vars
c_step      = 1
c_direction = 0
rotation    = 0

# Update Freq Var
bno_loop_time = 0
bmp_loop_time = 0

# Data Vars
temperature = 0
pressure    = 0
compass     = 0

def buildScrCompass():
    global fonts, disps, cps_elems, conf_map

    # Compass Screen
    if conf_map["COMPASS"]:
        disp["SCR"].append(Rect(disp["DISP"].width//2 - 2, 0,  4, 16,  fill = 0xFFFFFF, outline = None, stroke = 0))
        disp["SCR"].append(Rect(disp["DISP"].width - 16, disp["DISP"].height//2 - 2,  16, 4,  fill = 0xFFFFFF, outline = None, stroke = 0))
        disp["SCR"].append(Rect(disp["DISP"].width//2 - 2, disp["DISP"].height - 16,  4, 16,  fill = 0xFFFFFF, outline = None, stroke = 0))
        disp["SCR"].append(Rect(0, disp["DISP"].height//2 - 2,  16, 4,  fill = 0xFFFFFF, outline = None, stroke = 0))
        cps_elems["pointer"] = Circle(disp["DISP"].width//2 + 0, 8, 6, fill=col_map[0][1], outline=None, stroke=0)

    if conf_map["COMPASS_DEG"]:
        cps_elems["label_dir"]  = label.Label(fonts[28], color = 0xFFFFFF, anchor_point = (0.5, 0.5), anchored_position = (120, 120))

    if conf_map["CARDINALS"]:
        cps_elems["label_card"] = label.Label(fonts[18], color = 0xFFFFFF, anchor_point = (0.5, 0.5), anchored_position = (120, 75))

    if conf_map["PRESSURE"]:
        cps_elems["label_baro"] = label.Label(fonts[12], color = 0xFFFFFF, anchor_point = (0.5, 0.5), anchored_position = (120, 166))

    if conf_map["TEMPERATURE"]:
        cps_elems["label_temp"] = label.Label(fonts[12], color = 0xFFFFFF, anchor_point = (0.5, 0.5), anchored_position = (120, 192))

    for elem in cps_elems:
        disp["SCR"].append(cps_elems[elem])

    disp["DISP"].refresh()

def deg2cardinal(rotation):
    if rotation >= 348 or rotation <= 12:
        return "N"
    elif rotation > 12 and rotation < 33:
        return "NNE"
    elif rotation >= 33 and rotation <= 56:
        return "NE"
    elif rotation > 56 and rotation < 78:
        return "ENE"
    elif rotation >= 78 and rotation <= 102:
        return "E"
    elif rotation > 102 and rotation < 123:
        return "ESE"
    elif rotation >= 123 and rotation <= 146:
        return "SE"
    elif rotation > 146 and rotation < 168:
        return "SSE"
    elif rotation >= 168 and rotation <= 192:
        return "S"
    elif rotation > 192 and rotation < 213:
        return "SSW"
    elif rotation >= 213 and rotation <= 236:
        return "SW"
    elif rotation > 236 and rotation < 258:
        return "WSW"
    elif rotation >= 258 and rotation <= 282:
        return "W"
    elif rotation > 282 and rotation < 303:
        return "WNW"
    elif rotation >= 303 and rotation <= 326:
        return "NW"
    elif rotation > 326 and rotation < 348:
        return "NNW"

def doCalibration():
    global bno055
    bno055.offsets_magnetometer = (211, -79, -215)
    bno055.offsets_gyroscope    = (-1, 0, 0)

def loadFonts():
    global fonts
    fonts[12] = bitmap_font.load_font("fonts/Droid_TP-12.bdf")
    fonts[18] = bitmap_font.load_font("fonts/Droid_Alpha-18.bdf")
    fonts[28] = bitmap_font.load_font("fonts/Droid_Num-28.bdf")

def loopBMP():
    global bmp_loop_time, cps_elems

    # Update Data @ ~0.2Hz
    n_loop_time = time.monotonic()
    if bmp_loop_time + 5 < n_loop_time:
        if conf_map["PRESSURE"]:
            cps_elems["label_baro"].text = "%d mbar" % (bmp280.pressure,)

        if conf_map["TEMPERATURE"]:
            cps_elems["label_temp"].text = "%d°C" % (bmp280.temperature,)

        bmp_loop_time = n_loop_time

def loopEuler():
    global bno_loop_time
    global compass, uart

    # Update Data @ ~4Hz
    n_loop_time = time.monotonic()
    if bno_loop_time + 0.25 < n_loop_time:
        try:
            sys, gyro, accel, mag = bno055.calibration_status
            euler                 = bno055.euler
        except:
            return

        if conf_map["COMPASS"] or conf_map["COMPASS_DEG"]:
            if mag >= 2:
                compass = euler[0]

        if conf_map["UART_LVL"]:
            pitch = 0
            roll  = 0

            if sys >= 2 or (gyro >= 2 and accel >= 1):
                pitch = euler[2]
                roll  = euler[1]

            # Send Pitch & Roll over UART (+000.00|-000.00)
            uart.write(b'%+07.2f|%+07.2f|%d|%d|%d\r\n' % (pitch, roll, sys, gyro, accel))

        bno_loop_time = n_loop_time

def setup():
    global disp, uart, i2c, bno055, bmp280, fonts

    displayio.release_displays()

    # Intialise Display/SPI Bus
    spi = busio.SPI(spi_int["CLK"], spi_int["MOSI"], None)

    # Get Lock to set Baud Rate
    while not spi.try_lock():
        pass

    spi.configure(baudrate=10000000)
    spi.unlock()

    # Initialise Display per SPI Bus
    disp_bus     = displayio.FourWire(spi, command = spi_int["DC"], chip_select = spi_int["CS"], reset = spi_int["RST"])
    disp["DISP"] = gc9a01.GC9A01(disp_bus, width = 240, height = 240)
    disp["SCR"]  = displayio.Group()

    disp["DISP"].auto_refresh = False
    disp["DISP"].rotation     = 0
    disp["DISP"].show(disp["SCR"])

    # Initialise BNO055 over I2C
    i2c    = busio.I2C(board.GP5, board.GP4)
    bno055 = adafruit_bno055.BNO055_I2C(i2c)
    bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)

    # Initialise UART
    uart   = busio.UART(board.GP0, board.GP1, baudrate = 115200)

    # Calibrations
    doCalibration()

    # Load Fonts
    loadFonts()

    # Build Screens
    buildScrCompass()

def loop():
    global conf_map, cps_elems, disp
    global temperature, pressure, compass
    global c_step, c_direction, rotation

    loopEuler()
    loopBMP()

    if conf_map["COMPASS"]:
        # Move Compass towards New Position
        if abs(round(compass) - rotation) >= 180:
            if round(compass) < rotation:
                r_direction = 1
            elif round(compass) > rotation:
                r_direction = -1
            else:
                r_direction = 0
        else:
            if round(compass) < rotation:
                r_direction = -1
            elif round(compass) > rotation:
                r_direction = 1
            else:
                r_direction = 0

        c_step = 2 if abs(round(compass) - rotation) >= 10 else 1

        if r_direction == -1:
            rotation = rotation - c_step if rotation < 360 else 0
            if rotation < 0:
                rotation = 360 + rotation
        elif r_direction == 1:
            rotation = rotation + c_step if rotation < 360 else 0
            if rotation > 359:
                rotation = rotation - 360

        x1 = round(112 * math.sin(rotation * (math.pi / 180)))
        y1 = round(112 * math.cos(rotation * (math.pi / 180)))

        cps_elems["pointer"].x0 = 120 + x1
        cps_elems["pointer"].y0 = 120 - y1

    if conf_map["COMPASS_DEG"]:
        cps_elems["label_dir"].text = "%03d" % (rotation,)

    if conf_map["CARDINALS"]:
        cps_elems["label_card"].text = deg2cardinal(rotation)

    disp["DISP"].refresh()


setup()
while True:
    loop()
