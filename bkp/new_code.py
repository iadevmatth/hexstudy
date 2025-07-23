import struct
import json
from datetime import datetime, timedelta

class SinocastelParser:
    def __init__(self, raw_hex_data, base_odometer_km=0):
        self.raw_bytes = bytes.fromhex(raw_hex_data)
        self.parsed_data = {}
        self.offset = 0
        self.base_odometer_km = base_odometer_km

    def _read(self, fmt, size):
        try:
            value = struct.unpack(f'<{fmt}', self.raw_bytes[self.offset : self.offset + size])[0]
            self.offset += size
            return value
        except (struct.error, IndexError):
            return None

    def _parse_vstate(self, vstate_value):
        if vstate_value & 0x00000400:
            return "ACC ON"
        return "No specific state detected"

    def _unix_to_datetime(self, unix_timestamp):
        if unix_timestamp is None:
            return None
        return datetime(2000, 1, 1) + timedelta(seconds=unix_timestamp)

    def _parse_login_packet(self):
        payload = {}
        payload["last_accon_time"] = self._unix_to_datetime(self._read("I", 4)).strftime("%Y-%m-%d %H:%M:%S")
        payload["utc_time"] = self._unix_to_datetime(self._read("I", 4)).strftime("%Y-%m-%d %H:%M:%S")

        device_meters = self._read("I", 4)
        payload["device_reported_mileage_meters"] = device_meters
        device_km = (device_meters / 1000.0) if device_meters is not None else 0
        payload["device_reported_mileage_km"] = round(device_km, 2)
        payload["calculated_vehicle_odometer_km"] = round(self.base_odometer_km + device_km, 2)

        payload["current_trip_mileage"] = self._read("I", 4)
        payload["total_fuel"] = self._read("I", 4)
        payload["current_fuel"] = self._read("H", 2)

        vstate_value = self._read("I", 4)
        payload["vstate_raw"] = f"0x{vstate_value:08x}"
        payload["vstate_decoded"] = self._parse_vstate(vstate_value)

        # Reserved field parsing
        protocol = self._read("B", 1)
        voltage_raw = self._read("B", 1)
        voltage = round(voltage_raw * 0.1 + 8, 1)
        network_info = self._read("B", 1)
        hardware_code = self._read("B", 1)
        signal_strength = self._read("B", 1)
        ber = self._read("B", 1)
        status_flags = self._read("H", 2)

        payload["reserved"] = {
            "protocol": "ISO9141" if protocol == 0x07 else f"unknown({protocol})",
            "voltage_V": voltage,
            "network": "CDMA BC0" if network_info == 0x01 else f"unknown({network_info})",
            "hardware_code": "SIM800L" if hardware_code == 0x07 else f"code_{hardware_code}",
            "signal_strength": signal_strength,
            "ber": ber,
            "status_flags": {
                "obd_connected": bool(status_flags & 0b0001),
                "rpm_present": bool(status_flags & 0b0010),
                "gps_error": bool(status_flags & 0b0100),
                "rtc_error": bool(status_flags & 0b1000),
                "voltage_error": bool(status_flags & 0b10000),
            }
        }

        # GPS
        gps_count = self._read("B", 1)
        payload["gps_info"] = []
        for _ in range(gps_count):
            gps = {}
            date = self.raw_bytes[self.offset:self.offset+3]; self.offset += 3
            time = self.raw_bytes[self.offset:self.offset+3]; self.offset += 3
            gps["date"] = f"{date[0]:02d}/{date[1]:02d}/20{date[2]:02d}"
            gps["time"] = f"{time[0]:02d}:{time[1]:02d}:{time[2]:02d}"
            lat_raw = self._read("I", 4)
            lon_raw = self._read("I", 4)
            lat = lat_raw / 3600000.0 if lat_raw else 0
            lon = lon_raw / 3600000.0 if lon_raw else 0
            speed = self._read("H", 2)
            direction = self._read("H", 2)
            flags = self._read("B", 1)
            gps.update({
                "latitude": lat if flags & 0x02 else -lat,
                "longitude": lon if flags & 0x01 else -lon,
                "speed_cm_s": speed,
                "direction_degrees": direction / 10.0,
                "latitude_direction": "N" if flags & 0x02 else "S",
                "longitude_direction": "E" if flags & 0x01 else "W",
                "fix_type": {0: "invalid", 1: "2D fix", 2: "3D fix"}.get((flags >> 2) & 0x03, "unknown"),
                "satellite_count": flags >> 4
            })
            payload["gps_info"].append(gps)

        # Software version (20 bytes ASCII)
        sw = self.raw_bytes[self.offset:self.offset+20]; self.offset += 20
        payload["software_version"] = sw.decode("ascii", errors="ignore").strip("\x00")

        # Hardware version (20 bytes ASCII)
        hw = self.raw_bytes[self.offset:self.offset+20]; self.offset += 20
        payload["hardware_version"] = hw.decode("ascii", errors="ignore").strip("\x00")

        # New parameter count (2 bytes)
        param_count = self._read("H", 2)
        payload["new_parameter_count"] = param_count
        params = []
        for _ in range(param_count):
            param = self.raw_bytes[self.offset:self.offset+2].hex().upper()
            self.offset += 2
            params.append(param)
        payload["new_parameters"] = params

        self.parsed_data["payload"] = payload

    def parse(self):
        self.parsed_data["protocol_head"] = f"0x{self.raw_bytes[self.offset:self.offset+2].hex()}"
        self.offset += 2
        self.parsed_data["protocol_length"] = self._read("H", 2)
        self.parsed_data["protocol_version"] = self._read("B", 1)

        device_id = self.raw_bytes[self.offset:self.offset+20]; self.offset += 20
        self.parsed_data["device_id"] = device_id.decode("ascii", errors="ignore").strip("\x00")

        protocol_id = self._read("H", 2)
        self.parsed_data["protocol_id"] = f"0x{protocol_id:04x}"

        if protocol_id == 0x1001:
            self._parse_login_packet()
        else:
            self.parsed_data["payload"] = f"Parser para o protocolo {hex(protocol_id)} não implementado."

        final_offset = len(self.raw_bytes) - 4
        self.offset = final_offset
        self.parsed_data["crc"] = f"0x{self._read('H', 2):04x}"
        self.parsed_data["protocol_tail"] = f"0x{self.raw_bytes[self.offset:self.offset+2].hex()}"

        return self.parsed_data

raw_hex_packet = "40409B000432313347445032303138303231333433000000001001A3311B5DAD321B5D6F3D000010020000C20100000A000000040000000400073B0157000000003B015700000000010207130A200A3283C3023007A9103D025C06AF4944445F3231335730315F532056322E312E37004944445F3231335730315F482056322E312E37000E0001180218011A011B011E011F021F031F041F051F061F071F012102217B290D0A"

# 3. Vamos calcular o odômetro base para o exemplo
# Odômetro do Painel: 107.236 km
# Odômetro do Dispositivo: 1.409,586 km
# Base = 107236 - 1409.586 = 105826.414 km
odometro_base_do_veiculo = 105826.41

# Inicializa o parser passando o odômetro base
parser = SinocastelParser(raw_hex_packet, base_odometer_km=odometro_base_do_veiculo)
parsed_result = parser.parse()

print(json.dumps(parsed_result, indent=4))