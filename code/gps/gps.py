import time

class GPS:

    def __init__(self):
        self.time = ""
        self.date = ""
        self.timestamp = 0
        self._time_updated = 0

        self.latitude = 0
        self.latitude_cardinal = "N"
        self.longitude = 0
        self.longitude_cardinal = "W"

        self.altitude = 0
        self.altitude_unit = "m"

        self.speed = 0
        self.course = 0

        self.fix = False

        self.hdop = 0
        self.vdop = 0
        self.pdop = 0

        self.satellites = {}

    """ PARSING FUNCTIONS """
    def parse(self, nmea_str):
        # Validate NMEA Sentence Checksum
        if not self.validate_chksum(nmea_str):
            print("FAILED CHECKSUM")
            print(nmea_str)
            return False

        # Call Parse Function for NMEA Sentence if Exists
        nmea_sentence_type  = nmea_str[2:5]
        nmea_data = nmea_str[:-3].split(",")
        if nmea_sentence_type == "GGA":
            self.parse_gga(nmea_data)
        elif nmea_sentence_type == "GLL":
            self.parse_gll(nmea_data)
        elif nmea_sentence_type == "GSA":
            self.parse_gsa(nmea_data)
        elif nmea_sentence_type == "GSV":
            self.parse_gsv(nmea_data)
        elif nmea_sentence_type == "RMC":
            self.parse_rmc(nmea_data)
        elif nmea_sentence_type == "VTG":
            pass
        else:
            print(f"GPS Library Missing: {nmea_sentence_type}")
            return False

    def parse_gga(self, nmea_data):
        # Time
        self.set_time(nmea_data[1])

        # Latitude
        self.latitude = nmea_data[2]
        self.latitude_cardinal = nmea_data[3]

        # Longitude
        self.longitude = nmea_data[4]
        self.longitude_cardinal = nmea_data[5]

        # Fix
        self.fix = True if int(nmea_data[6]) == 1 else False

        # Horizonal Dilution of Precision
        self.hdop = nmea_data[8]

        # Altitude
        try:
            self.altitude = float(nmea_data[9])
        except:
            pass
        self.altitude_unit = nmea_data[10]

    def parse_gll(self, nmea_data):
        # Latitude
        self.latitude = nmea_data[1]
        self.latitude_cardinal = nmea_data[2]

        # Longitude
        self.longitude = nmea_data[3]
        self.longitude_cardinal = nmea_data[4]

        # Time
        self.set_time(nmea_data[5])

    def parse_gsa(self, nmea_data):
        # Dilution of Precision
        self.pdop = nmea_data[len(nmea_data) - 4]
        self.hdop = nmea_data[len(nmea_data) - 3]
        self.vdop = nmea_data[len(nmea_data) - 2]

        # Satellites in View
        for i in range(3, len(nmea_data) - 5):
            if not nmea_data[i] == "":
                if nmea_data[i] not in self.satellites.keys():
                    self.satellites[nmea_data[i]] = {"isActive" : True, "time" : time.ticks_ms()}
                else:
                    self.satellites[nmea_data[i]]["isActive"] = True
                    self.satellites[nmea_data[i]]["time"]     = time.ticks_ms()

        for satellite in self.satellites:
            if time.ticks_ms() - 2000 > self.satellites[satellite]["time"]:
                del self.satellites[satellite]

    def parse_gsv(self, nmea_data):
        i = 4
        while i + 4 <= len(nmea_data):
            if nmea_data[i] not in self.satellites.keys():
                self.satellites[nmea_data[i]] = {"isActive" : False, "time" : time.ticks_ms(), "elevation" : nmea_data[i + 1], "azimuth" : nmea_data[i + 2], "snr" : nmea_data[i + 3], "network" : nmea_data[0][1:2]}
            else:
                self.satellites[nmea_data[i]]["time"]      = time.ticks_ms()
                self.satellites[nmea_data[i]]["elevation"] = nmea_data[i + 1]
                self.satellites[nmea_data[i]]["azimuth"]   = nmea_data[i + 2]
                self.satellites[nmea_data[i]]["snr"]       = nmea_data[i + 2]
                self.satellites[nmea_data[i]]["network"]   = nmea_data[0][1:2]
            i += 4

    def parse_rmc(self, nmea_data):
        # Date/Time
        self.set_time(nmea_data[1])
        if not nmea_data[9] == "":
            self.date = nmea_data[9][0:2] + "/" + nmea_data[9][2:4] + "/" + nmea_data[9][4:6]
            self.timestamp = time.mktime(((2000 + int(nmea_data[9][4:6])), int(nmea_data[9][2:4]), int(nmea_data[9][0:2]), int(nmea_data[1][0:2]), int(nmea_data[1][2:4]), int(nmea_data[1][4:6]), 0, 0))

        # Latitude
        self.latitude = nmea_data[3]
        self.latitude_cardinal = nmea_data[4]

        # Longitude
        self.longitude = nmea_data[5]
        self.longitude_cardinal = nmea_data[6]

        # Speed/Course
        try:
            self.speed = float(nmea_data[7])
        except:
            pass
        self.course = nmea_data[8]

    def validate_chksum(self, nmea_str):
        nmea_len = len(nmea_str)
        try:
            expected_chk = int(nmea_str[nmea_len - 2:nmea_len], 16)
        except:
            return False
        actual_chk   = 0

        for char in nmea_str[:-3]:
            actual_chk ^= ord(char)

        return actual_chk == expected_chk

    """ DATA FUNCTIONS """
    def is_time_advancing(self):
        return (time.ticks_ms() - self._time_updated) < 1200

    def get_altitude(self, unit):
        return self.altitude

    def get_date(self):
        return self.date

    def get_latitude(self):
        if not self.latitude:
            return 0.0

        return self.parse_degrees(self.latitude)

    def get_latitude_cardinal(self):
        if not self.latitude_cardinal:
            return ""

        return self.latitude_cardinal

    def get_longitude(self):
        if not self.longitude:
            return 0.0

        return self.parse_degrees(self.longitude)

    def get_longitude_cardinal(self):
        if not self.longitude_cardinal:
            return ""

        return self.longitude_cardinal

    def get_speed(self, unit):
        if unit == "mph":
            return self.speed * 1.15078
        elif unit == "kmph":
            return self.speed * 1.852
        else:
            return self.speed

    def get_time(self, precision="s"):
        if precision == "s":
            return self.time[:-2]
        else:
            return self.time

    def get_timestamp(self):
        return self.timestamp

    def has_fix(self):
        return self.fix

    def get_tracked_satellites(self):
        return len(self.satellites)

    def get_active_satellites(self):
        count = 0

        for satellite in self.satellites:
            if self.satellites[satellite]["isActive"]:
                count += 1

        return count

    def get_satellites(self):
        for satellite in self.satellites:
            if time.ticks_ms() - 2000 > self.satellites[satellite]["time"]:
                del self.satellites[satellite]

        return self.satellites

    def get_satellite_networks(self):
        networks = {"GA" : 0, "GB" : 0, "GL" : 0, "GP" : 0}

        # Loop Through All Satellites
        for satellite in self.satellites:
            # Skip Satellites Without Network
            if "network" not in self.satellites[satellite].keys():
                continue

            # Ignore Inactive Satellites
            if not self.satellites[satellite]["isActive"]:
                continue

            # Add Satellite To Count
            if "G" + self.satellites[satellite]["network"] in networks.keys():
                networks["G" + self.satellites[satellite]["network"]] += 1
            else:
                # Non Supported Satellite Networks
                print(f"Satellite Network G{self.satellites[satellite]["network"]} Not Implemented")

        return networks

    def parse_degrees(self, degrees):
        f_degrees = float(degrees)
        deg = f_degrees // 100
        minutes = f_degrees % 100
        return (deg + minutes / 60)

    def set_time(self, gps_time):
        if gps_time == "":
            return

        prev_time = self.time
        new_time = gps_time[0:2] + ":" + gps_time[2:4] + ":" + gps_time[4:6] + "." + gps_time[7:8]

        if not new_time == prev_time:
            self._time_updated = time.ticks_ms()

        self.time = new_time

