import board, math, time
import displayio, busio, terminalio
import gc9a01

from adafruit_display_shapes.Circle import Circle
from adafruit_display_shapes.Rect   import Rect
from adafruit_display_shapes.Line   import Line
from adafruit_display_text          import label
from adafruit_display_text          import bitmap_label
from adafruit_bitmap_font           import bitmap_font

# Initialised Variables
conf_map = {"LVL_BUBBLE" : True, "LVL_CROSSHAIR" : True, "PITCH" : True, "ROLL" : True, "UART_LVL" : True}
spi_int  = {"CLK" : board.GP6, "MOSI" : board.GP7, "DC" : board.GP10, "CS" : board.GP9, "RST" : board.GP11, "BLK" : board.GP12}
col_map  = [(15, 0x69B34C), (50, 0xFF8E15), (90, 0xFF0D0D)]

disp      = {}
fonts     = {}
lvl_elems = {}

# Movement Vars
x_step      = 1
y_step      = 1
x_direction = 0
y_direction = 0


# Data Vars
inclination = {"PITCH" : 0, "ROLL" : 0}
cal         = {"SYS" : 0, "GYRO" : 0, "ACCEL" : 0, "TIMER" : time.monotonic(), "LOST" : False, "X" : 0, "Y" : 0}

def buildScrLevel():
    global fonts, disps, lvl_elems, conf_map

    # Bubble Level Screen
    if conf_map["LVL_CROSSHAIR"]:
        disp["SCR"].append(Rect(disp["DISP"].width//2 - 12, disp["DISP"].height//2 - 1,  24, 2,  fill = 0xFFFFFF, outline = None, stroke = 0))
        disp["SCR"].append(Rect(disp["DISP"].width//2 - 1,  disp["DISP"].height//2 - 12, 2,  24, fill = 0xFFFFFF, outline = None, stroke = 0))

    if conf_map["LVL_BUBBLE"]:
        lvl_elems["level"] = Circle(disp["DISP"].width//2 + 0, disp["DISP"].height//2 - 0, 35, fill = None, outline = col_map[0][1], stroke = 8)

    if conf_map["PITCH"]:
        disp["SCR"].append(Line(20, 112, 20, 128, color = 0xFFFFFF))
        disp["SCR"].append(Line(20, 112, 16, 116, color = 0xFFFFFF))
        disp["SCR"].append(Line(20, 112, 24, 116, color = 0xFFFFFF))
        disp["SCR"].append(Line(20, 128, 16, 124, color = 0xFFFFFF))
        disp["SCR"].append(Line(20, 128, 24, 124, color = 0xFFFFFF))
        lvl_elems["PITCH"] = label.Label(fonts[12], color = 0xFFFFFF, anchor_point = (0, 0.5), anchored_position = (32, 120))

    if conf_map["ROLL"]:
        disp["SCR"].append(Line(112, 220, 128, 220, color = 0xFFFFFF))
        disp["SCR"].append(Line(112, 220, 116, 216, color = 0xFFFFFF))
        disp["SCR"].append(Line(112, 220, 116, 224, color = 0xFFFFFF))
        disp["SCR"].append(Line(128, 220, 124, 216, color = 0xFFFFFF))
        disp["SCR"].append(Line(128, 220, 124, 224, color = 0xFFFFFF))
        lvl_elems["ROLL"] = label.Label(fonts[12], color = 0xFFFFFF, anchor_point = (0.5, 1.0), anchored_position = (120, 208))

    for elem in lvl_elems:
        disp["SCR"].append(lvl_elems[elem])

    disp["DISP"].refresh()

def loadFonts():
    global fonts
    fonts[12] = bitmap_font.load_font("fonts/Droid_TP-12.bdf")
    fonts[18] = bitmap_font.load_font("fonts/Droid_Alpha-18.bdf")
    fonts[28] = bitmap_font.load_font("fonts/Droid_Num-28.bdf")

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

    # Initialise UART
    uart   = busio.UART(board.GP0, board.GP1, baudrate = 115200, timeout = 0.002)

    # Load Fonts
    loadFonts()

    # Build Screens
    buildScrLevel()

def loop():
    global uart, inclination, lvl_elems, cal

    data  = uart.read(23)
    if not data == None:
        try:
            inclination["PITCH"] = float(data[0:7])
            inclination["ROLL"]  = float(data[8:15])
            cal["SYS"]           = int(data[16:17])
            cal["GYRO"]          = int(data[18:19])
            cal["ACCEL"]         = int(data[20:21])
        except:
            return


        # Only update text as received
        if conf_map["LVL_BUBBLE"] and not cal["LOST"]:
            if conf_map["PITCH"]:
                if abs(inclination["PITCH"]) >= 10:
                    lvl_elems["PITCH"].text = "%d" % (-inclination["PITCH"],)
                else:
                    lvl_elems["PITCH"].text = "%.1f" % (-inclination["PITCH"],)

            if conf_map["ROLL"]:
                if abs(inclination["ROLL"]) >= 10:
                    lvl_elems["ROLL"].text = "%d" % (inclination["ROLL"],)
                else:
                    lvl_elems["ROLL"].text = "%.1f" % (inclination["ROLL"],)

        if cal["LOST"]:
            lvl_elems["PITCH"].text = ""
            lvl_elems["ROLL"].text  = ""


    # Calibration Error
    if cal["SYS"] < 2 or (cal["GYRO"] < 2 and cal["ACCEL"] < 1):
        local_timer = time.monotonic()
        if not cal["LOST"]:
            cal["LOST"] = True
            cal["X"] = lvl_elems["level"].x0
            cal["Y"] = lvl_elems["level"].y0
        if cal["TIMER"] + 0.2 <= local_timer:
            lvl_elems["level"].outline = col_map[2][1]
            lvl_elems["level"].fill = None
            lvl_elems["level"].x0 = 0 if lvl_elems["level"].x0 != 0 else cal["X"]
            lvl_elems["level"].y0 = 0 if lvl_elems["level"].y0 != 0 else cal["Y"]
            cal["TIMER"] = local_timer
        disp["DISP"].refresh()
        return
    elif cal["LOST"]:
        cal["LOST"] = False
        lvl_elems["level"].x0 = cal["X"]
        lvl_elems["level"].y0 = cal["Y"]
        disp["DISP"].refresh()
        return
                


    if conf_map["LVL_BUBBLE"]:
        # Get Bubble Level Position
        x0 = lvl_elems["level"].x0
        y0 = lvl_elems["level"].y0

        # Move Bubble Level towards New Position
        x_target = (round(inclination["ROLL"] * 6)) + 120
        y_target = (round(inclination["PITCH"] * 6)) + 120
        x_step   = 2 if abs(x_target - x0) >= 10 else 1
        y_step   = 2 if abs(y_target - y0) >= 10 else 1

        if x0 > x_target:
            lvl_elems["level"].x0 = x0 - x_step
        elif x0 < x_target:
            lvl_elems["level"].x0 = x0 + x_step

        if y0 > y_target:
            lvl_elems["level"].y0 = y0 - y_step
        elif y0 < y_target:
            lvl_elems["level"].y0 = y0 + y_step

        # Update Bubble Level Colour
        scaleX = x0 - 120 if x0 >= 120 else 120 - x0
        scaleY = y0 - 120 if y0 >= 120 else 120 - y0
        scaleXY = scaleX if scaleX > scaleY else scaleY

        for key, colour in col_map:
            if scaleXY <= key:
                lvl_elems["level"].outline = colour
                lvl_elems["level"].fill = None
                break

    # Refresh Display
    disp["DISP"].refresh()


setup()
while True:
    loop()
