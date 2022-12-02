import board, math, time
import displayio, busio, terminalio
import gc9a01

from adafruit_display_shapes.RoundRect import RoundRect
from adafruit_display_shapes.Line      import Line
from adafruit_display_shapes.Circle    import Circle
from adafruit_display_text.label       import Label
from adafruit_display_text             import bitmap_label
from adafruit_bitmap_font              import bitmap_font

# Initialised Variables
conf_map = {}
spi_int  = {"CLK" : board.GP6, "MOSI" : board.GP7, "DC" : board.GP10, "CS" : board.GP9, "RST" : board.GP11, "BLK" : board.GP12}
col_map  = [0x69B34C, 0xFF8E15, 0xFF0D0D, 0x000000]

disp       = {}
fonts      = {}
tpms_elems = {}

tpms       = {"P_FL" : 0.0, "P_FR" : 0.0, "P_BL" : 0.0, "P_BR" : 0.0, "P_SP" : 0.0, "T_FL" : 0.0, "T_FR" : 0.0, "T_BL" : 0.0, "T_BR" : 0.0, "T_SP" : 0.0}
limits     = {"P_FL" : 50, "P_FR" : 50, "P_BL" : 68, "P_BR" : 68, "P_SP" : 50, "TEMP" : 30}
blink      = {"FL" : False, "FR" : False, "BL" : False, "BR" : False, "SP" : False}

loop_time  = time.monotonic()

def buildScrTPMS():
    global fonts, disp, tpms_elems, conf_map, col_map

    van_bmp = displayio.OnDiskBitmap("/img/van.bmp")
    disp["SCR"].append(displayio.TileGrid(van_bmp, pixel_shader=van_bmp.pixel_shader))

    tpms_elems["LBL_P_FL"] = Label(fonts[12], text = "0.0", color = 0xFFFFFF, anchor_point = (0.5, 0.5), anchored_position = (40, 60))
    tpms_elems["LBL_P_BL"] = Label(fonts[12], text = "0.0", color = 0xFFFFFF, anchor_point = (0.5, 0.5), anchored_position = (40, 159))
    tpms_elems["LBL_P_FR"] = Label(fonts[12], text = "0.0", color = 0xFFFFFF, anchor_point = (0.5, 0.5), anchored_position = (200, 60))
    tpms_elems["LBL_P_BR"] = Label(fonts[12], text = "0.0", color = 0xFFFFFF, anchor_point = (0.5, 0.5), anchored_position = (200, 159))
    tpms_elems["LBL_P_SP"] = Label(fonts[12], text = "0.0", color = 0xFFFFFF, anchor_point = (0.5, 0.5), anchored_position = (120, 140))

    tpms_elems["LBL_T_FL"] = Label(fonts[12], text = "0.0", color = 0xFFFFFF, anchor_point = (0.5, 0.5), anchored_position = (40, 81))
    tpms_elems["LBL_T_BL"] = Label(fonts[12], text = "0.0", color = 0xFFFFFF, anchor_point = (0.5, 0.5), anchored_position = (40, 180))
    tpms_elems["LBL_T_FR"] = Label(fonts[12], text = "0.0", color = 0xFFFFFF, anchor_point = (0.5, 0.5), anchored_position = (200, 81))
    tpms_elems["LBL_T_BR"] = Label(fonts[12], text = "0.0", color = 0xFFFFFF, anchor_point = (0.5, 0.5), anchored_position = (200, 180))
    tpms_elems["LBL_T_SP"] = Label(fonts[12], text = "0.0", color = 0xFFFFFF, anchor_point = (0.5, 0.5), anchored_position = (120, 161))

    tpms_elems["TYRE_FL"]  = RoundRect(64,  54,  10, 33, 4, fill = col_map[0], stroke = 1, outline = 0xEEEEEE)
    tpms_elems["TYRE_BL"]  = RoundRect(64,  154, 10, 33, 4, fill = col_map[0], stroke = 1, outline = 0xEEEEEE)
    tpms_elems["TYRE_FR"]  = RoundRect(166, 54,  10, 33, 4, fill = col_map[0], stroke = 1, outline = 0xEEEEEE)
    tpms_elems["TYRE_BR"]  = RoundRect(166, 154, 10, 33, 4, fill = col_map[0], stroke = 1, outline = 0xEEEEEE)
    tpms_elems["TYRE_SP"]  = Circle(120, 188, 13, fill = col_map[0], stroke = 1, outline = 0xEEEEEE)
    tpms_elems["TYRE_S2"]  = Circle(120, 188, 8,  fill = 0x000000,   stroke = 1, outline = 0xEEEEEE)

    tpms_elems["SEP_FL"]   = Line(24,  70,  56,  70,  color = 0x808080)
    tpms_elems["SEP_BL"]   = Line(24,  169, 56,  169, color = 0x808080)
    tpms_elems["SEP_FR"]   = Line(216, 70,  184, 70,  color = 0x808080)
    tpms_elems["SEP_BR"]   = Line(216, 169, 184, 169, color = 0x808080)
    tpms_elems["SEP_SP"]   = Line(104, 150, 136, 150, color = 0x808080)

    tpms_elems["KEY_P"]    = Label(fonts[12], text="psi", color = 0xFFFFFF, anchor_point = (0.5, 0.5), anchored_position = (120, 90))
    tpms_elems["KEY_T"]    = Label(fonts[12], text="°C",  color = 0xFFFFFF, anchor_point = (0.5, 0.5), anchored_position = (120, 114))

    for elem in tpms_elems:
        disp["SCR"].append(tpms_elems[elem])

    disp["DISP"].refresh()

def loadFonts():
    global fonts
    fonts[12] = bitmap_font.load_font("fonts/Droid_TPMS-12.bdf")

def setup():
    global disp, uart, fonts

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
    uart = busio.UART(None, board.GP1, baudrate = 9600, timeout = 0.008)

    # Load Fonts
    loadFonts()

    # Build Screens
    buildScrTPMS()

def loop():
    global uart, tpms_elems, disp, tpms, limits, blink, loop_time

    data  = uart.read(62)
    if not data == None:
        try:
            tpms["P_FL"] = float(data[0:5])
            tpms["T_FL"] = float(data[6:11])
            tpms["P_FR"] = float(data[12:17])
            tpms["T_FR"] = float(data[18:23])
            tpms["P_BL"] = float(data[24:29])
            tpms["T_BL"] = float(data[30:35])
            tpms["P_BR"] = float(data[36:41])
            tpms["T_BR"] = float(data[42:47])
            tpms["P_SP"] = float(data[48:53])
            tpms["T_SP"] = float(data[54:59])
        except:
            return

    for loc in ("FL", "FR", "BL", "BR", "SP"):
        if (tpms["P_" + loc] <= limits["P_" + loc] * 0.7) or (tpms["T_" + loc] >= limits["TEMP"] * 1.4):
            tpms_elems["TYRE_" + loc].fill = col_map[2]
            blink[loc] = True
        elif (tpms["P_" + loc] <= limits["P_" + loc] * 0.85) or (tpms["T_" + loc] >= limits["TEMP"] * 1.15):
            tpms_elems["TYRE_" + loc].fill = col_map[1]
        else:
            tpms_elems["TYRE_" + loc].fill = col_map[0]

        if tpms["P_" + loc] >= 10:
            tpms_elems["LBL_P_" + loc].text = "%2d" % (tpms["P_" + loc],)
        else:
            tpms_elems["LBL_P_" + loc].text = "%01.1f" % (tpms["P_" + loc],)

        if tpms["T_" + loc] >= 10:
            tpms_elems["LBL_T_" + loc].text = "%2d" % (tpms["T_" + loc],)
        else:
            tpms_elems["LBL_T_" + loc].text = "%01.1f" % (tpms["T_" + loc],)

    n_loop_time = time.monotonic()
    if loop_time + 0.25 <= n_loop_time:
        for loc in ("FL", "FR", "BL", "BR", "SP"):
            if blink[loc]:
                col = tpms_elems["TYRE_" + loc].fill
                if col == col_map[3]:
                    tpms_elems["TYRE_" + loc].fill = col_map[2]
                elif col == col_map[2]:
                    tpms_elems["TYRE_" + loc].fill = col_map[3]
        loop_time = n_loop_time

    disp["DISP"].refresh()


setup()
while True:
    loop()
