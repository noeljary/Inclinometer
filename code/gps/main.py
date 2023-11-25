from machine import I2C, Pin, SPI, UART
from gps import GPS
import _thread
import time
import gc9a01
import cst816
import math
import framebuf

# Images and Fonts
import img.altitude, img.satellite
import font.droid42_num, font.droid18_clk, font.droid15_gps


"""GPS FUNCTIONS"""
# Parse GPS NMEA Sentences into GPS Object
def gps_parser():
    global gps # Access GPS Object in Parser Thread

    # Instantiate UART Connection to u-blox NEO-M9N
    uart =  UART(0, baudrate=38400, rx=Pin(1), rxbuf=4096, timeout=200)

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


""" DATA MANIPULATION FUNCTIONS """
def mph2kmph(mph):
    return mph * 1.609344

def mph2kn(mpg):
    return mph / 1.151

def m2ft(m):
    return m * 3.281


""" NO TIME FIX SPLASH VIEW """
def init_splash():
    # Blank Slate
    fbuf.fill(0)

    # Satellite Image
    fbuf.bitmap(img.satellite, 112, 87, 0, 0x0000)

def print_splash():
    # Change Screen if Time Fix
    if gps.get_timestamp() > 0 and gps.is_time_advancing():
        return "NOFIX"

    # Print Satellite Counts
    active_sats = gps.get_active_satellites()
    tracked_sats = gps.get_tracked_satellites()
    fbuf.rect(102, 112, 36, 36, 0x0000, True)
    fbuf.write(font.droid15_gps, f"{active_sats}", 120, 120, 0xffff, 0x0000, True)
    fbuf.write(font.droid15_gps, f"({tracked_sats})", 120, 140, 0xffff, 0x0000, True)

    # Move Spinner Around
    spinner(fbuf)

    tft.blit_buffer(fbuf, 0, 0, 240, 240)


""" NO GEO FIX SPLASH VIEW """
def init_splash2():
    # Blank Slate
    fbuf.fill(0)

    # Satellite Image
    fbuf.bitmap(img.satellite, 112, 132, 0, 0x0000)

def print_splash2():
    # Advance Screen if GPS Fix
    if gps.fix:
        return "LOCATION"

    # Return to Previous Screen if Time Lost
    if not gps.is_time_advancing():
        return "NOTIME"

    # Print Satellite Counts
    active_sats = gps.get_active_satellites()
    tracked_sats = gps.get_tracked_satellites()
    fbuf.rect(102, 157, 36, 36, 0x0000, True)
    fbuf.write(font.droid15_gps, f"{active_sats}", 120, 165, 0xffff, 0x0000, True)
    fbuf.write(font.droid15_gps, f"({tracked_sats})", 120, 185, 0xffff, 0x0000, True)

    # Print Date and Time
    fbuf.write(font.droid18_clk, gps.get_date(), 120, 68, 0xffff, 0x0000, True)
    fbuf.write(font.droid18_clk, gps.get_time(), 120, 90, 0xffff, 0x0000, True)

    # Move Spinner Around
    spinner(fbuf)

    tft.blit_buffer(fbuf, 0, 0, 240, 240)


""" LOCATION VIEW """
def init_gps():
    # Blank Slate
    fbuf.fill(0)

    # Images
    fbuf.bitmap(img.satellite, 32, 90, 0, 0x0000)
    fbuf.bitmap(img.altitude, 192, 90, 0, 0x0000)

    # Units
    speed_unit = gps_conf["SPEED_UNITS"][gps_conf["SPEED_UNIT"]][1]
    altitude_unit = gps_conf["ALT_UNITS"][gps_conf["ALT_UNIT"]][1]
    fbuf.write(font.droid15_gps, speed_unit, 120, 150, 0xffff, 0x0000, True)
    fbuf.write(font.droid15_gps, altitude_unit, 200, 140, 0xffff, 0x0000, True) # Speed Units

def print_gps():
    # Hide if Fix Lost
    if not gps.fix:
        return "NOFIX"
    
    # Print Date and Time
    fbuf.write(font.droid18_clk, gps.get_date(), 120, 40, 0xffff, 0x0000, True)
    fbuf.write(font.droid18_clk, gps.get_time(), 120, 62, 0xffff, 0x0000, True)

    # Print Speed
    speed = gps.get_speed(gps_conf["SPEED_UNITS"][gps_conf["SPEED_UNIT"]][1])
    if callable(gps_conf["SPEED_UNITS"][gps_conf["SPEED_UNIT"]][2]):
        speed = gps_conf["SPEED_UNITS"][gps_conf["SPEED_UNIT"]][2](speed)

    fbuf.rect(83, 105, 75, 30, 0x0000, True)
    fbuf.write(font.droid42_num, f"{speed:.0f}", 120, 120, 0xffff, 0x000, True)

    # Print Altitude
    altitude = gps.get_altitude(gps_conf["ALT_UNITS"][gps_conf["ALT_UNIT"]][1])
    if callable(gps_conf["ALT_UNITS"][gps_conf["ALT_UNIT"]][2]):
        altitude = gps_conf["ALT_UNITS"][gps_conf["ALT_UNIT"]][2](altitude)

    fbuf.rect(178, 114, 45, 16, 0x0000, True)    
    fbuf.write(font.droid15_gps, f"{altitude:.0f}", 200, 122, 0xffff, 0x0000, True)

    # Print Satellite Counts
    active_sats = gps.get_active_satellites()
    tracked_sats = gps.get_tracked_satellites()
    fbuf.rect(22, 114, 36, 36, 0x0000, True)
    fbuf.write(font.droid15_gps, f"{active_sats}", 40, 122, 0xffff, 0x0000, True)
    fbuf.write(font.droid15_gps, f"({tracked_sats})", 40, 140, 0xffff, 0x0000, True)

    # Print Latitude and Longitude
    fbuf.write(font.droid15_gps, f"{gps.get_latitude():09.6f}°{gps.get_latitude_cardinal()}", 120, 187, 0xffff, 0x0000, True)
    fbuf.write(font.droid15_gps, f"{gps.get_longitude():09.6f}°{gps.get_longitude_cardinal()}", 120, 207, 0xffff, 0x0000, True) # Longitude

    tft.blit_buffer(fbuf, 0, 0, 240, 240)


"""SKY MAP VIEW"""
def print_sky():
    fbuf.fill(0)
    fbuf.vline(120, 0, 240, 0xffff)
    fbuf.hline(0, 120, 240, 0xffff)
    fbuf.ellipse(120, 120, 40, 40, 0xffff)
    fbuf.ellipse(120, 120, 75, 75, 0xffff)
    fbuf.ellipse(120, 120, 110, 110, 0xffff)

    for sat in gps.get_satellites():
        if "elevation" in gps.satellites[sat].keys():
            radius = round(int(gps.satellites[sat]["elevation"]) * 1.33)
            angle = int(gps.satellites[sat]["azimuth"])
            active = gps.satellites[sat]["isActive"]
            colour = gps_conf["SAT_COLOURS"][gps.satellites[sat]["network"]]

            x = round(120 + (radius * math.sin(angle * (math.pi / 180))))
            y = round(120 - (radius * math.cos(angle * (math.pi / 180))))

            fbuf.ellipse(x, y, 5, 5, colour, active)

    tft.blit_buffer(fbuf, 0, 0, 240, 240)


""" LOADING SPINNER """
def spinner(fb):
    # Circle Colour
    active_sats = gps.get_active_satellites()
    colour = gps_conf["STAT_COLOURS"][active_sats if active_sats <= 3 else 3]

    # Blank Old Circle
    x = 120 + round(108 * math.sin(gps_conf["SPIN_ROTATION"] * (math.pi / 180)))
    y = 120 - round(108 * math.cos(gps_conf["SPIN_ROTATION"] * (math.pi / 180)))
    fb.ellipse(x, y, 6, 6, 0x0000, True)

    # Increase Spinner Rotation
    gps_conf["SPIN_ROTATION"] += 2 if gps_conf["SPIN_ROTATION"] < 360 else -358

    # Draw New Circle
    x = 120 + round(108 * math.sin(gps_conf["SPIN_ROTATION"] * (math.pi / 180)))
    y = 120 - round(108 * math.cos(gps_conf["SPIN_ROTATION"] * (math.pi / 180)))
    fb.ellipse(x, y, 6, 6, colour, True)


""" SCREEN SLIDER """
def slide(gesture, coords):
    position = None
    # If Gesture is Left/Right
    if gesture in (cst816.CST816_Gesture_Left, cst816.CST816_Gesture_Right):
        # Find Current Sreen Order Position
        for screen in range(0, len(gps_conf["SLIDE_ORDER"])):
            if gps_conf["SLIDE_ORDER"][screen] == active_scr:
                position = screen
                break
        
        # Fail if Screen Not Found
        if position is None:
            return
    else:
        return

    if gesture == cst816.CST816_Gesture_Left:
        position = (position + 1) % len(gps_conf["SLIDE_ORDER"])
    elif gesture == cst816.CST816_Gesture_Right:
        position = (position - 1) % len(gps_conf["SLIDE_ORDER"])

    return gps_conf["SLIDE_ORDER"][position]


# Function Map for Screen Setup
active_scr = "NOTIME"
screens = {
    "NOTIME"   : (init_splash, print_splash, None , 50),
    "NOFIX"    : (init_splash2, print_splash2, None, 50),
    "LOCATION" : (init_gps, print_gps, slide, 200),
    "SKYMAP"   : (None, print_sky, slide, 1000)
}

# GPS Config
gps_conf = {
     "SPIN_ROTATION" : -2,
     "TIMEZONE" : 0,
     "SLIDE_ORDER" : ("LOCATION", "SKYMAP"),
     "SAT_COLOURS" : {"A" : 0x9F04, "B" : 0x38FC, "L" : 0x8427, "P" : 0x28FE},
     "STAT_COLOURS" : [0x61F8, 0x61F8, 0x62FC, 0x896D],
     "SPEED_UNITS" : [("Miles", "mph", None), ("Kilometres", "kmph", mph2kmph), ("Knots", "kn", mph2kn)],
     "ALT_UNITS" : [("Metres", "m", None), ("Feet", "ft", m2ft)],
     "SPEED_UNIT" : 0,
     "ALT_UNIT" : 0
}

# Instantiate GPS Parser Object
gps = GPS()

# Instantiate GPS Parser Thread
second_thread = _thread.start_new_thread(gps_parser, ())

# Create Global FrameBuffer
fbuf = framebuf.FrameBuffer(bytearray(115200), 240, 240, framebuf.RGB565)

# Hardware Initialisation
spi = SPI(0, baudrate=40000000, sck=Pin(2), mosi=Pin(3)) # SPI Bus
i2c = I2C(0, scl=Pin(13), sda=Pin(12), freq=400000) # I2C Bus
touch = cst816.CST816(i2c, 2, 14, 15) # Touch Screen
tft = gc9a01.GC9A01( # Display
    spi,
    240,
    240,
    dc=Pin(6, Pin.OUT),
    cs=Pin(5, Pin.OUT),
    reset=Pin(7, Pin.OUT),
    backlight=Pin(8, Pin.OUT),
    rotation=0
)

# Initial Display Template
tft.init()
tft.fill(0)
time.sleep(0.1)
tft.on()


while True:
    # Screen Initialisation
    if callable(screens[active_scr][0]):
        action = screens[active_scr][0]()
        if action is not None:
            active_scr = action
            continue

    display_refresh = 0
    while True:
        # Redraw Screen
        n_time = time.ticks_ms()
        if display_refresh + screens[active_scr][3] <= n_time and callable(screens[active_scr][1]):
            display_refresh = n_time
            #t1 = time.ticks_ms()
            action = screens[active_scr][1]()
            #t2 = time.ticks_ms() - t1
            #print(t2)
            if action is not None:
                active_scr = action
                display_refresh = 0
                break

        # Touch Handling
        t_ev = touch.read_trigger()
        if t_ev[0] and callable(screens[active_scr][2]):
            action = screens[active_scr][2](*t_ev[1])
            if action is not None:
                active_scr = action
                display_refresh = 0
                break
