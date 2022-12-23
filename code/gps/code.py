import board, time, math
import displayio, busio
import gc9a01
import adafruit_gps

from adafruit_display_text.label import Label
from adafruit_bitmap_font import bitmap_font

# Initialised Variables
conf_map = {}
spi_int = {
    "CLK": board.GP6,
    "MOSI": board.GP7,
    "DC": board.GP10,
    "CS": board.GP9,
    "RST": board.GP11,
    "BLK": board.GP12,
}
col_map = [0x69B34C, 0xFF8E15, 0xFF0D0D, 0x000000]

disp = {}
fonts = {}
gps_elems = {}

uart = None
gps = None

last_print = time.monotonic()

def buildScrGPS():
    global disp, gps_elems, fonts

    # Satellite Counter
    sat_bmp = displayio.OnDiskBitmap("/img/sat.bmp")
    disp["SCR"].append(displayio.TileGrid(sat_bmp, pixel_shader=sat_bmp.pixel_shader, width=1, height=1, tile_width=16, tile_height=16, x=32, y=90))
    gps_elems["LBL_SATS_IN_VIEW"] = Label(fonts[12], text = "0", color = 0xFFFFFF, anchor_point = (0.5, 0.5), anchored_position = (40, 120))
    gps_elems["LBL_SATS"] = Label(fonts[12], text = "(0)", color = 0xFFFFFF, anchor_point = (0.5, 0.5), anchored_position = (40, 140))

    # GPS Position
    gps_elems["LBL_LAT"] = Label(fonts[12], text = "00.000000°N", color = 0xFFFFFF, anchor_point = (1.0, 0.5), anchored_position = (175, 185))
    gps_elems["LBL_LNG"] = Label(fonts[12], text = "00.000000°W", color = 0xFFFFFF, anchor_point = (1.0, 0.5), anchored_position = (175, 205))

    # Datetime
    gps_elems["LBL_DATE"] = Label(fonts[14], text = "00/00/00", color = 0xFFFFFF, anchor_point = (0.5, 0.5), anchored_position = (120, 35))
    gps_elems["LBL_TIME"] = Label(fonts[14], text = "00:00:00", color = 0xFFFFFF, anchor_point = (0.5, 0.5), anchored_position = (120, 57))

    # Speed
    gps_elems["LBL_SPEED"] = Label(fonts[32], text = "0", color = 0xFFFFFF, anchor_point = (0.5, 0.5), anchored_position = (120, 118))
    gps_elems["LBL_SPEED_UNIT"] = Label(fonts[12], text = "mph", color = 0xFFFFFF, anchor_point = (0.5, 0.5), anchored_position = (120, 146))

    # Altitude
    alt_bmp = displayio.OnDiskBitmap("/img/alt.bmp")
    disp["SCR"].append(displayio.TileGrid(alt_bmp, pixel_shader=alt_bmp.pixel_shader, width=1, height=1, tile_width=16, tile_height=16, x=192, y=90))
    gps_elems["LBL_ALT"] = Label(fonts[12], text = "0", color = 0xFFFFFF, anchor_point = (0.5, 0.5), anchored_position = (200, 120))
    gps_elems["LBL_ALT_UNIT"] = Label(fonts[12], text = "m", color = 0xFFFFFF, anchor_point = (0.5, 0.5), anchored_position = (200, 138))

    for elem in gps_elems:
        disp["SCR"].append(gps_elems[elem])

    disp["DISP"].refresh()

def loadFonts():
    global fonts
    fonts[12] = bitmap_font.load_font("/fonts/Droid_GPS-12.bdf")
    fonts[14] = bitmap_font.load_font("/fonts/Droid_CLK-14.bdf")
    fonts[32] = bitmap_font.load_font("/fonts/Droid_Num-32.bdf")

def setup():
    global disp, uart, gps

    displayio.release_displays()

    # Intialise Display/SPI Bus
    spi = busio.SPI(spi_int["CLK"], spi_int["MOSI"], None)

    # Get Lock to set Baud Rate
    while not spi.try_lock():
        pass

    spi.configure(baudrate=10000000)
    spi.unlock()

    # Initialise Display per SPI Bus
    disp_bus = displayio.FourWire(
        spi, command=spi_int["DC"], chip_select=spi_int["CS"], reset=spi_int["RST"]
    )
    disp["DISP"] = gc9a01.GC9A01(disp_bus, width=240, height=240)
    disp["SCR"] = displayio.Group()
    disp["DISP"].auto_refresh = False
    disp["DISP"].rotation = 0
    disp["DISP"].show(disp["SCR"])
    disp["DISP"].refresh()

    loadFonts()
    buildScrGPS()

    uart = busio.UART(board.GP0, board.GP1, baudrate=9600, timeout=1)
    gps = adafruit_gps.GPS(uart, debug=False)


def loop():
    global gps, last_print, disp, gps_elems

    gps.update()

    current = time.monotonic()
    if current - last_print >= 1.0:
        last_print = current

        if gps.satellites is not None:
            gps_elems["LBL_SATS_IN_VIEW"].text = "%d" % gps.satellites_in_view
            gps_elems["LBL_SATS"].text = "(%d)" % gps.satellites

            if gps.timestamp_utc is not None:
                gps_elems["LBL_DATE"].text = "%02d/%02d/%02d" % (gps.timestamp_utc.tm_mday, gps.timestamp_utc.tm_mon, gps.timestamp_utc.tm_year - 2000)
                gps_elems["LBL_TIME"].text = "%02d:%02d:%02d" % (gps.timestamp_utc.tm_hour, gps.timestamp_utc.tm_min, gps.timestamp_utc.tm_sec)

        if not gps.has_fix:
            print("Waiting for fix...")
            return

        gps_lat = abs(gps.latitude)
        gps_lng = abs(gps.longitude)
        gps_elems["LBL_LAT"].text = f"{gps_lat:.6f}°{gps.latitude_card}"
        gps_elems["LBL_LNG"].text = f"{gps_lng:.6f}°{gps.longitude_card}"

        gps_elems["LBL_SPEED"].text = "%d" % round(gps.speed_knots * 1.15)

        if gps.has_3d_fix and gps.altitude_m is not None:
            gps_elems["LBL_ALT"].text = "%d" % gps.altitude_m

    disp["DISP"].refresh()

setup()
while True:
    loop()
