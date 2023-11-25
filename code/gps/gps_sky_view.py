from machine import I2C, Pin, SPI, UART
from gps import GPS
import _thread
import time
import gc9a01
import cst816
import math
import framebuf

# Images and Fonts
import altitude, satellite
import droid42_num, droid18_clk, droid15_gps

"""HELPER FUNCTIONS"""
# Print Bitmap Image to Framebuffer
def bitmap(fb, bmp, x, y):
    bs_bit = 0
    for i in range(0, bmp.HEIGHT * bmp.WIDTH):
        colour_idx = 0
        for bit in range(bmp.BPP):
            colour_idx <<= 1
            colour_idx |= (bmp.BITMAP[bs_bit // 8] & 1 << (7 - (bs_bit % 8))) > 0
            bs_bit += 1
        colour = bmp.PALETTE[colour_idx]      
        fb.pixel(x + (i % bmp.WIDTH), y + (i // bmp.WIDTH), colour)

# Print Text to Frambuffer
def write(fb, font, text, x, y, fg, bg):
    for char in text:
        if char in font.MAP:
            char_idx = font.MAP.index(char)
            offset = char_idx * font.OFFSET_WIDTH
            bs_bit = font.OFFSETS[offset]

            if font.OFFSET_WIDTH > 2:
                bs_bit = (bs_bit << 8) + font.OFFSETS[offset + 2]
            elif font.OFFSET_WIDTH > 1:
                bs_bit = (bs_bit << 8) + font.OFFSETS[offset + 1]  

            char_width = font.WIDTHS[char_idx]

            for i in range(0, char_width * font.HEIGHT):
                co_X = x + (i % char_width)
                co_Y = y + (i // char_width)
                if font.BITMAPS[bs_bit // 8] & 1 << (7 - (bs_bit % 8)) > 0:
                    fb.pixel(co_X, co_Y, fg)
                else:
                    fb.pixel(co_X, co_Y, bg)
                bs_bit += 1
            x += char_width
        else:
            continue


"""GPS FUNCTIONS"""
# Parse GPS NMEA Sentences into GPS Object
def gps_parser():
    global gps # Access GPS Object in Parser Thread

    # Instantiate UART Connection to u-blox NEO-M9N
    uart =  UART(0, baudrate=38400, rx=Pin(17), rxbuf=4096, timeout_char=200, timeout=200)

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
            colour = sat_col[gps.satellites[sat]["network"]]

            x = round(120 + (radius * math.sin(angle * (math.pi / 180))))
            y = round(120 - (radius * math.cos(angle * (math.pi / 180))))

            fbuf.ellipse(x, y, 5, 5, colour, active)

    tft.blit_buffer(fbuf, 0, 0, 240, 240)

def touch_sky(gesture, coords):
    if gesture == cst816.CST816_Gesture_Left:
        return active_scr + 1 if active_scr + 1 <= len(screens) - 2 and len(screens) > 1 else 0
    elif gesture == cst816.CST816_Gesture_Right:
        return active_scr - 1 if active_scr - 1 >= 0 and len(screens) > 1 else len(screens) - 2


"""PRIMARY NAV VIEW"""
def init_gps():
    # Erase Comparison Values 
    global main_scr_cmp
    main_scr_cmp = {"DATETIME" : (0, 0, 0, 0, 0, 0, 0, 0), "SATS_ACTIVE" : 0, "SATS_TRACKED" : 0, "SPEED" : 0, "ALTITUDE" : 0, "LATITUDE" : 0.0, "LONGITUDE" : 0.0, "LATITUDE_CARDINAL" : "", "LONGITUDE_CARDINAL" : ""}

    fbuf.fill(0) # Blank Screen

    bitmap(fbuf, satellite, 32, 90) # Satellite Image
    bitmap(fbuf, altitude, 192, 90) # Altitude Image

    write(fbuf, droid18_clk, "00/00/00" if not gps.fix else gps.get_date(), 76, 35, gc9a01.WHITE, gc9a01.BLACK) # Date
    write(fbuf, droid18_clk, "00:00:00" if not gps.fix else gps.get_time(), 76, 57, gc9a01.WHITE, gc9a01.BLACK) # Time
    write(fbuf, droid15_gps, "00" if not gps.fix else f"{gps.get_active_satellites():02d}", 32, 115, gc9a01.WHITE, gc9a01.BLACK) # Active Satellite Count
    write(fbuf, droid15_gps, "(00)" if not gps.fix else f"({gps.get_tracked_satellites():02d})", 23, 133, gc9a01.WHITE, gc9a01.BLACK) # Tracked Satellite Count 
    write(fbuf, droid15_gps, "0000" if not gps.fix else f"{gps.get_altitude('m'):04.0f}", 183, 115, gc9a01.WHITE, gc9a01.BLACK) # Altitude
    write(fbuf, droid15_gps, "m", 196, 133, gc9a01.WHITE, gc9a01.BLACK) # Alitude Units
    write(fbuf, droid42_num, "00" if not gps.fix else f"{gps.get_speed('mph'):02.0f}", 95, 106, gc9a01.WHITE, gc9a01.BLACK) # Speed
    write(fbuf, droid15_gps, "mph", 106, 143, gc9a01.WHITE, gc9a01.BLACK) # Speed Units
    write(fbuf, droid15_gps, "00.000000°N" if not gps.fix else f"{gps.get_latitude():09.6f}°{gps.get_latitude_cardinal()}", 70, 180, gc9a01.WHITE, gc9a01.BLACK) # Latitude
    write(fbuf, droid15_gps, "00.000000°E" if not gps.fix else f"{gps.get_longitude():09.6f}°{gps.get_longitude_cardinal()}", 70, 200, gc9a01.WHITE, gc9a01.BLACK) # Longitude
    tft.blit_buffer(fbuf, 0, 0, 240, 240) # Write to Display

def print_gps():
    # Update Date/Time Labels
    datetime = time.gmtime(gps.get_timestamp() + (tz * 3600))
    if not datetime[0] == main_scr_cmp["DATETIME"][0]:
        write(fbuf, droid18_clk, f"{(datetime[0] - 2000):02d}", 142, 35, gc9a01.WHITE, gc9a01.BLACK)
    if not datetime[1] == main_scr_cmp["DATETIME"][1]:
        write(fbuf, droid18_clk, f"{datetime[1]:02d}", 109, 35, gc9a01.WHITE, gc9a01.BLACK)
    if not datetime[2] == main_scr_cmp["DATETIME"][2]:
        write(fbuf, droid18_clk, f"{datetime[2]:02d}", 76, 35, gc9a01.WHITE, gc9a01.BLACK)
    if not datetime[3] == main_scr_cmp["DATETIME"][3]:
        write(fbuf, droid18_clk, f"{datetime[3]:02d}", 76, 57, gc9a01.WHITE, gc9a01.BLACK)
    if not datetime[4] == main_scr_cmp["DATETIME"][4]:
        write(fbuf, droid18_clk, f"{datetime[4]:02d}", 109, 57, gc9a01.WHITE, gc9a01.BLACK)
    if not datetime[5] == main_scr_cmp["DATETIME"][5]:
        write(fbuf, droid18_clk, f"{datetime[5]:02d}", 142, 57, gc9a01.WHITE, gc9a01.BLACK)
    if not datetime == main_scr_cmp["DATETIME"]:
        main_scr_cmp["DATETIME"] = datetime

    # Update Speed Label
    speed = round(gps.get_speed("mph"))
    if not speed == main_scr_cmp["SPEED"]:
        write(fbuf, droid42_num, f"{speed:02d}", 95, 106, gc9a01.WHITE, gc9a01.BLACK)
        main_scr_cmp["SPEED"] = speed

    # Update Active Satellites Label
    active_sats = gps.get_active_satellites()
    if not active_sats == main_scr_cmp["SATS_ACTIVE"]:
        write(fbuf, droid15_gps, f"{active_sats:02d}", 32, 115, gc9a01.WHITE, gc9a01.BLACK)
        main_scr_cmp["SATS_ACTIVE"] = active_sats

    # Update Tracked Satellites Label
    tracked_sats = gps.get_tracked_satellites()
    if not tracked_sats == main_scr_cmp["SATS_TRACKED"]:
        write(fbuf, droid15_gps, f"{tracked_sats:02d}", 32, 133, gc9a01.WHITE, gc9a01.BLACK)
        main_scr_cmp["SATS_TRACKED"] = tracked_sats

    # Update Altitude Label
    altitude = round(gps.get_altitude("m"))
    if not altitude == main_scr_cmp["ALTITUDE"]:
        write(fbuf, droid15_gps, f"{altitude:04d}", 183, 115, gc9a01.WHITE, gc9a01.BLACK)
        main_scr_cmp["ALTITUDE"] = altitude

    # Update Latitude Label
    latitude = gps.get_latitude()
    if not latitude == main_scr_cmp["LATITUDE"]:
        write(fbuf, droid15_gps, f"{latitude:09.6f}", 70, 180, gc9a01.WHITE, gc9a01.BLACK)
        main_scr_cmp["LATITUDE"] = latitude

    # Update Longitude Label
    longitude = gps.get_longitude()
    if not longitude == main_scr_cmp["LONGITUDE"]:
        write(fbuf, droid15_gps, f"{longitude:09.6f}", 70, 200, gc9a01.WHITE, gc9a01.BLACK)
        main_scr_cmp["LONGITUDE"] = longitude

    # Update Latitude Cardinal Label
    latitude_cardinal = gps.get_latitude_cardinal()
    if not latitude_cardinal == main_scr_cmp["LATITUDE_CARDINAL"]:
        write(fbuf, droid15_gps, f"{latitude_cardinal}", 160, 180, gc9a01.WHITE, gc9a01.BLACK)
        main_scr_cmp["LATITUDE_CARDINAL"] = latitude_cardinal

    # Update Longitude Cardinal Label
    longitude_cardinal = gps.get_longitude_cardinal()
    if not longitude_cardinal == main_scr_cmp["LONGITUDE_CARDINAL"]:
        write(fbuf, droid15_gps, f"{longitude_cardinal}", 160, 200, gc9a01.WHITE, gc9a01.BLACK)
        main_scr_cmp["LONGITUDE_CARDINAL"] = longitude_cardinal

    # Write to Display
    tft.blit_buffer(fbuf, 0, 0, 240, 240)

def touch_gps(gesture, coords):
    if gesture == cst816.CST816_Gesture_Left:
        return active_scr + 1 if active_scr + 1 <= len(screens) - 2 and len(screens) > 1 else 0
    elif gesture == cst816.CST816_Gesture_Right:
        return active_scr - 1 if active_scr - 1 >= 0 and len(screens) > 1 else len(screens) - 2
 

"""SPLASH SCREEN VIEW"""
def init_splash(move = False):
    # Erase Comparison Values 
    global main_scr_cmp
    main_scr_cmp = {"DATETIME" : (0, 0, 0, 0, 0, 0, 0, 0), "SATS_ACTIVE" : 0, "SATS_TRACKED" : 0, "MOVED" : move}

    fbuf.fill(0) # Blank Screen

    y = 87 if not main_scr_cmp["MOVED"] else 132
    bitmap(fbuf, satellite, 112, y) # Satellite Image
    write(fbuf, droid15_gps, "00", 112, y + 25, gc9a01.WHITE, gc9a01.BLACK) # Active Satellite Count
    write(fbuf, droid15_gps, "(00)", 103, y + 45, gc9a01.WHITE, gc9a01.BLACK) # Tracked Satellite Count 

    if main_scr_cmp["MOVED"]:
        write(fbuf, droid18_clk, "00/00/00" if gps.get_timestamp() <= 0 else gps.get_date(), 76, 60, gc9a01.WHITE, gc9a01.BLACK) # Date
        write(fbuf, droid18_clk, "00:00:00" if gps.get_timestamp() <= 0 else gps.get_time(), 76, 82, gc9a01.WHITE, gc9a01.BLACK) # Time

    # Write to Display
    tft.blit_buffer(fbuf, 0, 0, 240, 240)

def print_splash():
    global spin_rotation

    # Date Fix Available so Move Satellite Counter
    if gps.get_timestamp() > 0 and not main_scr_cmp["MOVED"]:
        init_splash(True)

    # Calulate Element Positions
    y = 112 if not main_scr_cmp["MOVED"] else 157

    # Update Active Satellites Label
    active_sats = gps.get_active_satellites()
    if not active_sats == main_scr_cmp["SATS_ACTIVE"]:
        write(fbuf, droid15_gps, f"{active_sats:02d}", 112, y, gc9a01.WHITE, gc9a01.BLACK)
        main_scr_cmp["SATS_ACTIVE"] = active_sats

    # Update Tracked Satellites Label
    tracked_sats = gps.get_tracked_satellites()
    if not tracked_sats == main_scr_cmp["SATS_TRACKED"]:
        write(fbuf, droid15_gps, f"{tracked_sats:02d}", 112, y + 20, gc9a01.WHITE, gc9a01.BLACK)
        main_scr_cmp["SATS_TRACKED"] = tracked_sats

    # Update Date/Time Labels
    if gps.get_timestamp() > 0:
        datetime = time.gmtime(gps.get_timestamp() + (tz * 3600))
        if not datetime[0] == main_scr_cmp["DATETIME"][0]:
            write(fbuf, droid18_clk, f"{(datetime[0] - 2000):02d}", 142, 60, gc9a01.WHITE, gc9a01.BLACK)
        if not datetime[1] == main_scr_cmp["DATETIME"][1]:
            write(fbuf, droid18_clk, f"{datetime[1]:02d}", 109, 60, gc9a01.WHITE, gc9a01.BLACK)
        if not datetime[2] == main_scr_cmp["DATETIME"][2]:
            write(fbuf, droid18_clk, f"{datetime[2]:02d}", 76, 60, gc9a01.WHITE, gc9a01.BLACK)
        if not datetime[3] == main_scr_cmp["DATETIME"][3]:
            write(fbuf, droid18_clk, f"{datetime[3]:02d}", 76, 82, gc9a01.WHITE, gc9a01.BLACK)
        if not datetime[4] == main_scr_cmp["DATETIME"][4]:
            write(fbuf, droid18_clk, f"{datetime[4]:02d}", 109, 82, gc9a01.WHITE, gc9a01.BLACK)
        if not datetime[5] == main_scr_cmp["DATETIME"][5]:
            write(fbuf, droid18_clk, f"{datetime[5]:02d}", 142, 82, gc9a01.WHITE, gc9a01.BLACK)
        if not datetime == main_scr_cmp["DATETIME"]:
            main_scr_cmp["DATETIME"] = datetime
        
    # Circle Colour
    colour = stat_col[active_sats if active_sats <= 3 else 3]
    
    # Blank Old Circle
    x = 120 + round(110 * math.sin(spin_rotation * (math.pi / 180)))
    y = 120 - round(110 * math.cos(spin_rotation * (math.pi / 180)))
    fbuf.ellipse(x, y, 7, 7, 0x0000, True)

    # Increase Spinner Rotation
    spin_rotation += 2 if spin_rotation <= 360 else -360

    # Draw New Circle
    x = 120 + round(110 * math.sin(spin_rotation * (math.pi / 180)))
    y = 120 - round(110 * math.cos(spin_rotation * (math.pi / 180)))
    fbuf.ellipse(x, y, 6, 6, colour, True)

    # Write to Display
    tft.blit_buffer(fbuf, 0, 0, 240, 240)

    # Move to Primary Nav View if GPS Fixed
    if gps.fix:
        return 0


# Function Map for Screen Setup
active_scr = 2
screens = (
    (init_gps, print_gps, touch_gps, 200),
    (None, print_sky, touch_sky, 1000),
    (init_splash, print_splash, None , 65)
)

# Create Global FrameBuffer
fbuf = framebuf.FrameBuffer(bytearray(115200), 240, 240, framebuf.RGB565)

# Display Colour Structures
stat_col = {0 : 0x61F8, 1 : 0x61F8, 2 : 0x62FC, 3 : 0x896D}
sat_col = {"A" : 0x9f04, "B" : 0x38fc, "L" : 0x8427, "P" : 0x28fe}

# Previous GPS Values
main_scr_cmp = {}

# Loading Spinner
spin_rotation = 0

# Current Timezone Offset
tz = 0

# Instantiate GPS Parser Object
gps = GPS()

# Instantiate GPS Parser Thread
second_thread = _thread.start_new_thread(gps_parser, ())

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
tft.off()
tft.fill(0)
tft.init()
tft.on()


while True:
    # Screen Initialisation
    if callable(screens[active_scr][0]):
        screens[active_scr][0]()

    display_refresh = time.ticks_ms()
    while True:
        # Redraw Screen
        n_time = time.ticks_ms()
        if display_refresh + screens[active_scr][3] <= n_time:
            display_refresh = n_time
            action = screens[active_scr][1]()
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


