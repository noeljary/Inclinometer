from machine import Pin, SPI, UART
from gps import GPS
import _thread
import time
import gc9a01py as gc9a01

# Images and Fonts
import altitude, satellite
import droid32_num, droid14_clk, droid12_gps


# Instantiate GPS Parser Object
gps = GPS()


# Parse GPS NMEA Sentences into GPS Object
def gps_parser():
    global gps # Access GPS Object in Parser Thread
    
    # Instantiate UART Connection to u-blox NEO-M9N
    uart =  UART(0, baudrate=38400, tx=Pin(0), rx=Pin(1), rxbuf=4096, timeout_char=200, timeout=200)
    
    # Change Update Frequency & Message Rates
    uart.write(b'\xb5\x62\x06\x8a\x0a\x00\x00\x01\x00\x00\x01\x00\x21\x30\xc8\x00\xb5\x81')
    time.sleep_ms(750)
    uart.write(b'\xb5\x62\x06\x8a\x13\x00\x00\x01\x00\x00\xc5\x00\x91\x20\x05\xb1\x00\x91\x20\x00\xc0\x00\x91\x20\x05\xf7\xb0')
    time.sleep_ms(750)

    # Clear rxBuf
    uart.read(uart.any())

    # Parser Loop
    while True:
        # Ensure Data in UART rxBuf
        if not uart.any():
            continue

        # Read & Parse Line Data
        nmea = uart.readline()
        gps.parse(''.join([chr(b) for b in nmea[1:-2]]))


# Display GPS Data on Screen
def print_gps():
    global tft
    tft.write(droid14_clk, gps.get_date(), 80, 35, gc9a01.WHITE, gc9a01.BLACK)
    tft.write(droid14_clk, gps.get_time(), 80, 57, gc9a01.WHITE, gc9a01.BLACK)
    tft.write(droid32_num, f"{gps.get_speed('mph'):02.0f}", 100, 108, gc9a01.WHITE, gc9a01.BLACK)
    tft.write(droid12_gps, f"{gps.get_active_satellites():02d}", 34, 115, gc9a01.WHITE, gc9a01.BLACK)
    tft.write(droid12_gps, f"({gps.get_tracked_satellites():02d})", 26, 135, gc9a01.WHITE, gc9a01.BLACK)
    tft.write(droid12_gps, f"{gps.get_altitude('m'):04.0f}", 183, 115, gc9a01.WHITE, gc9a01.BLACK)
    tft.write(droid12_gps, f"{gps.get_latitude():09.6f}°{gps.get_latitude_cardinal()}", 76, 180, gc9a01.WHITE, gc9a01.BLACK)
    tft.write(droid12_gps, f"{gps.get_longitude():09.6f}°{gps.get_longitude_cardinal()}", 76, 200, gc9a01.WHITE, gc9a01.BLACK)


# Instantiate GPS Parser Thread
second_thread = _thread.start_new_thread(gps_parser, ())

# Instantiate SPI Connection at 40MHz
spi = SPI(0, baudrate=40000000, sck=Pin(2), mosi=Pin(3))

# Initialise Display Object
tft = gc9a01.GC9A01(
    spi,
    dc=Pin(27, Pin.OUT),
    cs=Pin(26, Pin.OUT),
    reset=Pin(28, Pin.OUT),
    backlight=Pin(29, Pin.OUT),
    rotation=0
)

# Setup Display Template
tft.fill(0)
tft.bitmap(satellite, 32, 90)
tft.bitmap(altitude, 192, 90)
tft.write(droid14_clk, "00/00/00", 80, 35, gc9a01.WHITE, gc9a01.BLACK)
tft.write(droid14_clk, "00:00:00", 80, 57, gc9a01.WHITE, gc9a01.BLACK)
tft.write(droid12_gps, "mph", 109, 140, gc9a01.WHITE, gc9a01.BLACK)
tft.write(droid12_gps, "m", 196, 135, gc9a01.WHITE, gc9a01.BLACK)
tft.backlight(1)

display_refresh = time.ticks_ms()
while True:
    n_time = time.ticks_ms()
    if display_refresh + 200 <= n_time:
        display_refresh = n_time
        print_gps()
