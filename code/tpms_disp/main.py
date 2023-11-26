from machine import I2C, Pin, SPI, UART
import time
import gc9a01
import cst816
import framebuf
import array
import math
import json
import _thread

# Images and Fonts
import font.droid17, font.droid42_num
import img.van, img.cross48, img.cross32, img.tick48, img.tick32


""" DATA MANIPULATION FUNCTIONS """
def psi2bar(pressure):
    return (pressure / 14.504)

def psi2kpa(pressure):
    return (pressure * 6.895) 

def c2f(temperature):
    return ((temperature * (9/5)) + 32)

def c2k(temperature):
    return (temperature + 273.15)

def assign_scan_to_wheel(wheel):
    # Move Scan Elements to Nominated Wheel
    for key in tpms["SCAN"]:
        tpms["WHEELS"][wheel][key] = tpms["SCAN"][key]

    # Clear Down Scan Data
    reset_scan()

def delete_sensor(wheel):
    tpms["WHEELS"][wheel]["ID"] = None
    tpms["WHEELS"][wheel]["STATUS"] = None
    tpms["WHEELS"][wheel]["PRESSURE"] = None
    tpms["WHEELS"][wheel]["TEMPERATURE"] = None
    tpms["WHEELS"][wheel]["FLASH"] = False

def reset_scan():
    # Reset all Keys in Scan Object
    for key in tpms["SCAN"]:
        tpms["SCAN"][key] = None

def load_tpms_ids_from_file():
    # Load JSON TPMS ID File into Python Dict
    f = open("conf/tpms.json", "r")
    tpms_ids = json.loads(f.read())
    f.close()
    
    # Loop through Wheels and Assign IDs
    for wheel in tpms_ids:
        tpms["WHEELS"][wheel]["ID"] = tpms_ids[wheel]

def load_units_from_file():
    # Load JSON Units File into Python Dict
    f = open("conf/units.json")
    units = json.loads(f.read())
    f.close()
    
    # Loop through Units and Assign Values
    for unit in units:
        tpms[unit + "_UNIT"] = units[unit]

def save_tpms_ids_to_file():
    # Load JSON TPMS ID File into Python Dict
    f = open("conf/tpms.json", "r")
    tpms_ids = json.loads(f.read())
    f.close()
    
    # Loop through Wheels and Check for Changes
    rewrite = False
    for wheel in tpms_ids:
        if not tpms["WHEELS"][wheel]["ID"] == tpms_ids[wheel]:
            tpms_ids[wheel] = tpms["WHEELS"][wheel]["ID"]
            rewrite = True

    # Write New TPMS IDs to File
    f = open("conf/tpms.json", "w")
    f.write(json.dumps(tpms_ids))
    f.close()

def save_units_to_file():
    # Load JSON Units File into Python Dict
    f = open("conf/units.json", "r")
    units = json.loads(f.read())
    f.close()

    # Loop through Units and Check for Changes
    rewrite = False
    for unit in units:
        if not tpms[unit + "_UNIT"] == units[unit]:
            units[unit] = tpms[unit + "_UNIT"]
            rewrite = True

    # Write New Units to File
    f = open("conf/units.json", "w")
    f.write(json.dumps(units))
    f.close()


""" DRAWING HELPER FUNCTIONS """
def draw_wheel_end_view(fb, wheel, x, y, w, h):
    # Get Colour for Wheel Dependent on Pressure/Temperature
    colour = get_wheel_colour(wheel)

    # Co-ordinate Calculation Assists
    w2 = w // 2

    # Outline Wheel
    fb.ellipse(x + w2, y + w2, w2, w2, 0xffff, True)
    fb.ellipse(x + w2, y + h - w2, w2, w2, 0xffff, True)
    fb.vline(x, y + w2, h - w, 0xffff)
    fb.vline(x + w, y + w2, h - w, 0xffff)

    # Infill Wheel
    fb.ellipse(x + w2, y + w2, w2 - 1, w2 - 1, colour, True)
    fb.ellipse(x + w2, y + h - w2, w2 - 1, w2 - 1, colour, True)
    fb.rect(x + 1, y + w2, w - 1, h - w, colour , True)

def draw_wheel_face_view(fb, wheel, x, y, d):
    # Get Colour for Wheel Dependent on Pressure/Temperature
    colour = get_wheel_colour(wheel)

    # Co-ordinate Calculation Assists
    d2 = d // 2

    # White Outer Border Wheel
    fb.ellipse(x + d2, y + d2, d2, d2, 0xffff, True)
    # Colour Wheel
    fb.ellipse(x + d2, y + d2, d2 - 1, d2 - 1, colour, True)
    # White Inner Border Wheel
    fb.ellipse(x + d2, y + d2, round(d * 0.55) // 2, round(d * 0.55) // 2, 0xffff, True)
    # Black Inner Wheel
    fb.ellipse(x + d2, y + d2, (round(d * 0.55) // 2) - 1, (round(d * 0.55) // 2) - 1, 0x0000, True)

def draw_wheel_data(fb, wheel, x, y):
    # Clear Space
    fb.rect(x, y - 6, 30, 35, 0x0000, True)

    # Get Initial Pressure & Temperature Values
    pressure = tpms["WHEELS"][wheel]["PRESSURE"]
    temperature = tpms["WHEELS"][wheel]["TEMPERATURE"]

    # Convert Pressure Units if Required
    if pressure is not None and callable(tpms["PRESSURE_UNITS"][tpms["PRESSURE_UNIT"]][2]):
        pressure = tpms["PRESSURE_UNITS"][tpms["PRESSURE_UNIT"]][2](tpms["WHEELS"][wheel]["PRESSURE"])

    # Convert Temperature Units if Required
    if temperature and callable(tpms["TEMPERATURE_UNITS"][tpms["TEMPERATURE_UNIT"]][2]):
        temperature = tpms["TEMPERATURE_UNITS"][tpms["TEMPERATURE_UNIT"]][2](tpms["WHEELS"][wheel]["TEMPERATURE"])

    # Print Pressure or Placeholder
    if pressure is not None:
        dp = 1 if tpms["PRESSURE_UNITS"][tpms["PRESSURE_UNIT"]][3] else 0
        fb.write(font.droid17, f"{pressure:.{dp}f}", x + 15, y + 2, 0xffff, 0x0000, True)
    else:
        fb.write(font.droid17, "---", x + 15, y + 1, 0x1084, 0x0000, True)

    # Print Temperature or Placeholder
    if temperature is not None:
        fb.write(font.droid17, f"{temperature:.0f}", x + 15, y + 22, 0xffff, 0x0000, True)
    else:
        fb.write(font.droid17, "---", x + 15, y + 20, 0x1084, 0x0000, True)

    # Divider Line
    fbuf.hline(x, y + 10, 30, 0x1084)

def get_wheel_colour(wheel):
    # Get Tyre Pressure for Wheel
    pressure = tpms["WHEELS"][wheel]["PRESSURE"]

    # Get Target Pressure Value for Axle
    target = None
    for axle in tpms["TARGETS"]:
        if wheel in tpms["TARGETS"][axle]["WHEELS"]:
            target = tpms["TARGETS"][axle]["VALUE"]
            break

    # Get Indicator Level for Pressure Value
    indicator = None
    for level in tpms["LEVELS"]:
        if level["CHECK"] == "EQ_PCT": # Equals Percent
            if pressure == None or pressure == target * level["VALUE"]:
                indicator = level
                break
        elif level["CHECK"] == "LT_PCT": # Less Than Percent
            if pressure < target * level["VALUE"]:
                indicator = level
                break
        elif level["CHECK"] == "PM_PCT": # Plus/Minus Percent
            if pressure >= target - (target * level["VALUE"]) and pressure <= target + (target * level["VALUE"]):
                indicator = level
                continue
        elif level["CHECK"] == "GT_PCT": # Greater Than Percent
            if pressure > target * level["VALUE"]:
                indicator = level
                break

    # Flash Colour if Required by Indicator Level
    if indicator["FLASH"]:
        tpms["WHEELS"][wheel]["FLASH"] = not tpms["WHEELS"][wheel]["FLASH"]
        colour = 0x0000 if tpms["WHEELS"][wheel]["FLASH"] else indicator["COLOUR"]
        return colour

    return indicator["COLOUR"]


""" DEFAULT TPMS VIEW """
def init_tpms():
    # Blank Canvas
    fbuf.fill(0)

    # Background Image
    fbuf.bitmap(img.van, 81, 23, 0, 0x0000)

    # Units
    fbuf.write(font.droid17, tpms["PRESSURE_UNITS"][tpms["PRESSURE_UNIT"]][1], 120, 88, 0xffff, 0x0000, True)
    fbuf.write(font.droid17, f"°{tpms['TEMPERATURE_UNITS'][tpms['TEMPERATURE_UNIT']][1]}", 120, 112, 0xffff, 0x0000, True)

def print_tpms():
    # NSF
    draw_wheel_data(fbuf, "NSF", 24, 60)
    draw_wheel_end_view(fbuf, "NSF", 64, 54, 10, 33) 

    # NSR
    draw_wheel_data(fbuf, "NSR", 24, 160)
    draw_wheel_end_view(fbuf, "NSR", 64, 154, 10, 33) 

    # OSF
    draw_wheel_data(fbuf, "OSF", 184, 60)
    draw_wheel_end_view(fbuf, "OSF", 165, 54, 10, 33) 

    # OSR
    draw_wheel_data(fbuf, "OSR", 184, 160)
    draw_wheel_end_view(fbuf, "OSR", 165, 154, 10, 33) 

    # SPR
    draw_wheel_data(fbuf, "SPR", 105, 141)
    draw_wheel_face_view(fbuf, "SPR", 107, 174, 26) 

    tft.blit_buffer(fbuf, 0, 0, 240, 240)

def touch_tpms(gesture, coords):
    x = coords[0]
    y = coords[1]

    # Long Tap Only
    if not gesture == 12:
        return

    if x < 80 and y < 120: # Top Left
        tpms["FOCUS_WHEEL"] = "NSF"
        return "FOCUS"
    elif x < 80 and y > 120: # Bottom Left
        tpms["FOCUS_WHEEL"] = "NSR"
        return "FOCUS"
    elif x > 159 and y < 120: # Top Right
        tpms["FOCUS_WHEEL"] = "OSF"
        return "FOCUS"
    elif x > 159 and y > 120: # Bottom Right
        tpms["FOCUS_WHEEL"] = "OSR"
        return "FOCUS"
    elif x > 80 and x < 159 and y < 125: # Top Centre
        return "UNITS"
    elif x > 80 and x < 159 and y > 125: # Bottom Center
        tpms["FOCUS_WHEEL"] = "SPR"
        return "FOCUS"


""" WHEEL FOCUSED TPMS VIEW """
def init_focus():
    # Blank Canvas
    fbuf.fill(0)

    # Learn/Relearn Button
    fbuf.rect(0, 0, 240, 50, 0x61F8, True)    
    fbuf.write(font.droid17, "LEARN" if tpms["WHEELS"][tpms["FOCUS_WHEEL"]]["ID"] is None else "RELEARN", 120, 28, 0xffff, 0x61F8, True)

    # OK Button
    fbuf.rect(0, 190, 240, 50, 0x896D, True)
    fbuf.write(font.droid17, "OK", 120, 214, 0xffff, 0x896D, True)

    # TPMS Sensor ID
    sensor_id = f"0x{tpms['WHEELS'][tpms['FOCUS_WHEEL']]['ID']:07X}" if tpms["WHEELS"][tpms["FOCUS_WHEEL"]]["ID"] is not None else "Not Set"
    fbuf.write(font.droid17, f"ID:", 55, 64, 0xffff, 0x0000)
    fbuf.write(font.droid17, f"{sensor_id}", 95, 64, 0xffff, 0x0000)

    # Pressure Label
    fbuf.write(font.droid17, "Pressure:", 95, 94, 0xffff, 0x000)

    # Temperature Label
    fbuf.write(font.droid17, "Temperature:", 95, 141, 0xffff, 0x0000)

def print_focus():
    # Draw Wheel
    draw_wheel_face_view(fbuf, tpms["FOCUS_WHEEL"], 28, 110, 46)

    # Pressure
    pressure = tpms["WHEELS"][tpms["FOCUS_WHEEL"]]["PRESSURE"]
    pressure_unit = tpms["PRESSURE_UNITS"][tpms["PRESSURE_UNIT"]]

    # Temperature
    temperature = tpms["WHEELS"][tpms["FOCUS_WHEEL"]]["TEMPERATURE"]
    temperature_unit = tpms["TEMPERATURE_UNITS"][tpms["TEMPERATURE_UNIT"]]

    # Convert Pressure Units if Required
    if pressure is not None and callable(pressure_unit[2]):
        pressure = pressure_unit[2](tpms["WHEELS"][tpms["FOCUS_WHEEL"]]["PRESSURE"])

    # Print Pressure
    fbuf.rect(95, 115, 148, 17, 0x0000, True)
    if pressure is not None:
        dp = 1 if tpms["PRESSURE_UNITS"][tpms["PRESSURE_UNIT"]][3] else 0
        fbuf.write(font.droid17, f"{pressure:.{dp}f} {pressure_unit[1]}", 95, 115, 0xffff, 0x000)
    else:
        fbuf.write(font.droid17, f"--- {pressure_unit[1]}", 95, 115, 0xffff, 0x000)

    # Convert Temperature Units if Required
    if temperature and callable(temperature_unit[2]):
        temperature = temperature_unit[2](tpms["WHEELS"][tpms["FOCUS_WHEEL"]]["TEMPERATURE"])

    # Print Temperature
    fbuf.rect(95, 162, 148, 17, 0x0000, True)
    temperature = "---" if temperature is None else temperature
    fbuf.write(font.droid17, f"{temperature}°{temperature_unit[1]}", 95, 162, 0xffff, 0x0000)

    tft.blit_buffer(fbuf, 0, 0, 240, 240)

def touch_focus(gesture, coords):
    # Lower Button - Short Tap - Return to Default View
    if gesture == 5 and coords[1] > 190:
        return "TPMS"

    # Top Button - Long Tap - Move to Scanner View
    if gesture == 12 and coords[1] < 50:
        return "SCANNER"


""" UNITS CONTROL VIEW """
def init_units():
    # Blank Canvas
    fbuf.fill(0)

    # Header
    fbuf.rect(0, 0, 240, 50, 0x3B32, True)
    fbuf.write(font.droid17, "UNITS", 120, 28, 0xffff, 0x3B32, True)

    # OK Button
    fbuf.rect(0, 190, 240, 50, 0x896D, True)
    fbuf.write(font.droid17, "OK", 120, 214, 0xffff, 0x896D, True)

    # Pressure Lozenge
    fbuf.ellipse(45, 88, 26, 26, 0xffff, True)
    fbuf.ellipse(195, 88, 26, 26, 0xffff, True)
    fbuf.rect(45, 62, 150, 53, 0xffff, True)
    fbuf.poly(36, 88, array.array('h', [8, -8, 8, 8, 0, 0]), 0x1084, True)
    fbuf.poly(196, 80, array.array('h', [8, 8, 0, 16, 0, 0]), 0x1084, True)

    # Temperature Lozenge
    fbuf.ellipse(45, 152, 26, 26, 0xffff, True)
    fbuf.ellipse(195, 152, 26, 26, 0xffff, True)
    fbuf.rect(45, 126, 150, 53, 0xffff, True)
    fbuf.poly(36, 152, array.array('h', [8, -8, 8, 8, 0, 0]), 0x1084, True)
    fbuf.poly(196, 144, array.array('h', [8, 8, 0, 16, 0, 0]), 0x1084, True)

def print_units():
    # Print Pressure Unit
    pressure_unit = tpms["PRESSURE_UNITS"][tpms["PRESSURE_UNIT"]][0]
    fbuf.rect(60, 62, 120, 53, 0xffff, True)
    fbuf.write(font.droid17, pressure_unit, 120, 89, 0x0000, 0xffff, True)

    # Print Temperature Unit
    temperature_unit = tpms["TEMPERATURE_UNITS"][tpms["TEMPERATURE_UNIT"]][0]
    fbuf.rect(60, 126, 120, 53, 0xffff, True)
    fbuf.write(font.droid17, temperature_unit, 120, 153, 0x0000, 0xffff, True)

    tft.blit_buffer(fbuf, 0, 0, 240, 240)

def touch_units(gesture, coords):
    # Only Taps
    if gesture < 5:
        return

    # Lower Button - Return to Default View
    if coords[1] > 190:
        save_units_to_file()
        return "TPMS"

    # Cycle Through Pressure & Temperature Units
    if coords[0] < 100 and coords[1] > 52 and coords[1] < 118: # Left on Pressure
        tpms["PRESSURE_UNIT"] += -1 if tpms["PRESSURE_UNIT"] > 0 else len(tpms["PRESSURE_UNITS"]) - 1
    elif coords[0] > 140 and coords[1] > 52 and coords[1] < 118: # Right on Pressure
        tpms["PRESSURE_UNIT"] += 1 if tpms["PRESSURE_UNIT"] < len(tpms["PRESSURE_UNITS"]) - 1 else -(len(tpms["PRESSURE_UNITS"])) + 1
    elif coords[0] < 100 and coords[1] > 122 and coords[1] < 188: # Left on Temperature
        tpms["TEMPERATURE_UNIT"] += -1 if tpms["TEMPERATURE_UNIT"] > 0 else len(tpms["TEMPERATURE_UNITS"]) - 1
    elif coords[0] > 140 and coords[1] > 122 and coords[1] < 188: # Right on Temperature
        tpms["TEMPERATURE_UNIT"] += 1 if tpms["TEMPERATURE_UNIT"] < len(tpms["TEMPERATURE_UNITS"]) - 1 else -(len(tpms["PRESSURE_UNITS"])) + 1


""" SCANNER VIEW """
def init_scanner():
    # Remove Details from Old Sensor
    delete_sensor(tpms["FOCUS_WHEEL"])

    # Begin Scan Timer
    tpms["SCAN_START_TIME"] = time.ticks_ms()

    # Set Scanner Angle 
    tpms["SCANNER_ANGLE"] = 0

def print_scanner():
    # Blank Canvas
    fbuf.fill(0x896D)

    # Draw Spinner
    x = 120 + round(108 * math.sin(tpms["SCANNER_ANGLE"] * (math.pi / 180)))
    y = 120 - round(108 * math.cos(tpms["SCANNER_ANGLE"] * (math.pi / 180)))
    fbuf.ellipse(x, y, 6, 6, 0xffff, True)

    # Draw Timer Text
    time_remaining = abs(time.ticks_ms() - (tpms["SCAN_START_TIME"] + tpms["SCAN_TIME"] + 1000)) // 1000
    fbuf.write(font.droid42_num, f"{time_remaining}", 120, 120, 0xffff, 0x896D, True)

    # Increment Spinner Angle
    tpms["SCANNER_ANGLE"] += 2 if tpms["SCANNER_ANGLE"] < 360 else - 358

    tft.blit_buffer(fbuf, 0, 0, 240, 240)

    # If Sensor Found
    if tpms["SCAN"]["ID"] is not None:
        return "CONFIRM"

    # No Sensor Found
    if time_remaining == 0:
        return "FAIL"

def init_confirm():
    # Blank Canvas
    fbuf.fill(0)

    # Check if Found Sensor is used by another Wheel
    overlap = None
    for wheel in tpms["WHEELS"]:
        if tpms["WHEELS"][wheel]["ID"] == tpms["SCAN"]["ID"]:
            overlap = wheel

    if overlap:
        fbuf.write(font.droid17, f"Sensor 0x{tpms['SCAN']['ID']:07X}", 120, 58, 0xffff, 0x0000, True)
        fbuf.write(font.droid17, f"in use by {overlap}", 120, 78, 0xffff, 0x0000, True)
        fbuf.write(font.droid17, f"Move to {tpms['FOCUS_WHEEL']}?", 120, 108, 0xffff, 0x0000, True)
    else:
        fbuf.write(font.droid17, f"Sensor 0x{tpms['SCAN']['ID']:07X}", 120, 58, 0xffff, 0x0000, True)
        fbuf.write(font.droid17, "Discovered", 120, 78, 0xffff, 0x0000, True)
        fbuf.write(font.droid17, f"Assign to {tpms['FOCUS_WHEEL']}?", 120, 108, 0xffff, 0x0000, True)

    # Yes Button
    fbuf.ellipse(70, 170, 36, 36, 0x896D, True)
    fbuf.bitmap(img.tick32, 55, 155, 0, 0x896D)

    # No Button
    fbuf.ellipse(170, 170, 36, 36, 0x61F8, True)
    fbuf.bitmap(img.cross32, 155, 155, 0, 0x61F8)

    tft.blit_buffer(fbuf, 0, 0, 240, 240) 

def touch_confirm(gesture, coords):
    # Taps Only
    if gesture < 5:
        return

    if coords[0] < 120 and coords[1] > 120: # Yes
        # Check if Found Sensor is used by another Wheel
        for wheel in tpms["WHEELS"]:
            if tpms["WHEELS"][wheel]["ID"] == tpms["SCAN"]["ID"]:
                print(wheel)
                delete_sensor(wheel)

        # Assign Sensor to Focus Wheel
        assign_scan_to_wheel(tpms["FOCUS_WHEEL"])

        # Save New TPMS IDs
        save_tpms_ids_to_file()

        return "GOOD"
    elif coords[0] > 120 and coords[1] > 120: # No
        reset_scan()
        return "FOCUS"

def init_good():
    # Display Tick
    fbuf.fill(0x896D)
    fbuf.bitmap(img.tick48, 96, 96, 0, 0x896D)
    tft.blit_buffer(fbuf, 0, 0, 240, 240)

    # Wait 1s and Retun to Focus View
    time.sleep(1)
    return "FOCUS"

def init_fail():
    # Display Cross
    fbuf.fill(0x61F8)
    fbuf.bitmap(img.cross48, 96, 96, 0, 0x61F8)
    tft.blit_buffer(fbuf, 0, 0, 240, 240)

    # Wait 1a and Return to Focus View
    time.sleep(1)
    return "FOCUS"


""" TPMS UART RECEIVER """
def tpms_receiver():
    # Instantiate UART Connection to TPMS Receiver
    uart =  UART(0, baudrate=4800, rx=Pin(1), timeout=500)

    # Loop Forever waiting for Serial Data
    while True:
        # Read Data over Serial Connection
        tpms_data = uart.readline()

        # Only Proceed if Data Received
        if tpms_data is None:
            continue

        # Validate Data
        try:
            status, values = validate_tpms_chksum(tpms_data)
        except:
            return

        # Fail if Checksum does not Validate
        if not status:
            return

        # Match and Assign TPMS Sensor Values
        match_tpms_data(*values)

def validate_tpms_chksum(tpms_data):
    # Convert Bytearray to String
    tpms_str = ''.join([chr(b) for b in tpms_data])

    # Extract Checksum Content and Checksum Byte
    chksum_byte = int(tpms_str[len(tpms_str) - 2:], 16)
    chksum_str = tpms_str[:-3]

    # Calculate Checksum Byte from Content
    chksum_calc = 0
    for char in chksum_str:
        chksum_calc ^= ord(char)

    # Fail if Checksums do not match
    if not chksum_calc == chksum_byte:
        return (False, ())

    # Extract Values from Checksum Content String
    sensor_id, status, pressure, temperature, *other = chksum_str.split(",")

    return (True, (int(sensor_id, 16), int(status, 16), int(pressure), int(temperature)))

def match_tpms_data(sensor_id, status, pressure, temperature):
    # If System is within Scan Time and Nothing in Scan Receive Buffer
    if "SCAN_START_TIME" in tpms.keys() and tpms["SCAN_START_TIME"] + tpms["SCAN_TIME"] > time.ticks_ms() and tpms["SCAN"]["ID"] is None:
        print("SCANNED SENSOR")
        tpms["SCAN"]["ID"] = sensor_id
        tpms["SCAN"]["STATUS"] = status
        tpms["SCAN"]["PRESSURE"] = pressure
        tpms["SCAN"]["TEMPERATURE"] = temperature
        return

    # Standard Operation Assigning Received Data to Wheels while not Scanning
    for wheel in tpms["WHEELS"]:
        if tpms["WHEELS"][wheel]["ID"] == sensor_id:
            tpms["WHEELS"][wheel]["STATUS"] = status
            tpms["WHEELS"][wheel]["PRESSURE"] = pressure
            tpms["WHEELS"][wheel]["TEMPERATURE"] = temperature


""" BEGIN EXECUTION """

# Instantiate UART Receive Thread
second_thread = _thread.start_new_thread(tpms_receiver, ())

# Create Global FrameBuffer
fbuf = framebuf.FrameBuffer(bytearray(115200), 240, 240, framebuf.RGB565)

# Function Map for Screen Setup
active_scr = "TPMS"
screens = {
    "TPMS"    : (init_tpms, print_tpms, touch_tpms, 200),
    "FOCUS"   : (init_focus, print_focus, touch_focus, 200),
    "UNITS"   : (init_units, print_units, touch_units, 300),
    "SCANNER" : (init_scanner, print_scanner, None, 50),
    "CONFIRM" : (init_confirm, None, touch_confirm, 200),
    "GOOD"    : (init_good, None, None, 200),
    "FAIL"    : (init_fail, None, None, 200)
}

# TPMS Data
tpms = {
    "WHEELS": {
        "NSF" : {"ID" : None, "STATUS" : None, "PRESSURE" : None, "TEMPERATURE" : None, "FLASH" : False},
        "OSF" : {"ID" : None, "STATUS" : None, "PRESSURE" : None, "TEMPERATURE" : None, "FLASH" : False},
        "NSR" : {"ID" : None, "STATUS" : None, "PRESSURE" : None, "TEMPERATURE" : None, "FLASH" : False},
        "OSR" : {"ID" : None, "STATUS" : None, "PRESSURE" : None, "TEMPERATURE" : None, "FLASH" : False},
        "SPR" : {"ID" : None, "STATUS" : None, "PRESSURE" : None, "TEMPERATURE" : None, "FLASH" : False}
    },
    "SCAN"    : {"ID" : None, "STATUS" : None, "PRESSURE" : None, "TEMPERATURE" : None},
    "LEVELS": [
        {"ID" : "UNSET",     "CHECK" : "EQ_PCT", "VALUE" : -1,   "COLOUR" : 0x0000, "FLASH" : False},
        {"ID" : "EMERGENCY", "CHECK" : "LT_PCT", "VALUE" : 0.25, "COLOUR" : 0x61F8, "FLASH" : True},
        {"ID" : "CRITICAL",  "CHECK" : "LT_PCT", "VALUE" : 0.5,  "COLOUR" : 0x61F8, "FLASH" : False},
        {"ID" : "WARNING",   "CHECK" : "LT_PCT", "VALUE" : 0.9,  "COLOUR" : 0x62FC, "FLASH" : False},
        {"ID" : "OK",        "CHECK" : "PM_PCT", "VALUE" : 0.1,  "COLOUR" : 0x896D, "FLASH" : False},
        {"ID" : "HIGH",      "CHECK" : "GT_PCT", "VALUE" : 1.1,  "COLOUR" : 0x3B32, "FLASH" : False}
    ],
    "TARGETS" : {
        "FRONT_AXLE" : {"VALUE" : 51, "WHEELS" : ["NSF", "OSF"]},
        "REAR_AXLE"  : {"VALUE" : 52, "WHEELS" : ["NSR", "OSR"]},
        "SPARE"      : {"VALUE" : 52, "WHEELS" : ["SPR"]}
    },
    "PRESSURE_UNITS"    : [("PSI", "psi", None, False), ("Bar", "bar", psi2bar, True), ("kPa", "kpa", psi2kpa, False)], # (Unit, Symbol, Conversion Function, 1DP < 10)
    "TEMPERATURE_UNITS" : [("Celcius", "C", None), ("Farenheit", "F", c2f), ("Kelvin", "K", c2k)], # (Unit, Symbol, Conversion Function)
    "SCAN_TIME"         : 10000
}

# Load Data from File
load_tpms_ids_from_file()
load_units_from_file()

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
