import struct
import json

class SinocastelParser:
    def __init__(self, raw_hex_data):
        self.raw_bytes = bytes.fromhex(raw_hex_data)
        self.parsed_data = {}
        self.offset = 0

    def _read(self, fmt, size):
        try:
            value = struct.unpack(fmt, self.raw_bytes[self.offset : self.offset + size])[0]
            self.offset += size
            return value
        except (struct.error, IndexError):
            return None

    def _parse_vstate(self, vstate_value):
        states = []
        if (vstate_value & 0x00040000):
            states.append("ACC ON")
        
        if not states:
            return "No specific state detected"
        return ", ".join(states)

    def _parse_login_packet(self):
        payload = {}
        # ... (leitura dos campos anteriores continua a mesma)
        payload['last_accon_time'] = self._read('<I', 4)
        payload['utc_time'] = self._read('<I', 4)
        payload['total_trip_mileage'] = self._read('<I', 4)
        payload['current_trip_mileage'] = self._read('<I', 4)
        payload['total_fuel'] = self._read('<I', 4)
        payload['current_fuel'] = self._read('<H', 2)
        
        vstate_value = self._read('<I', 4)
        payload['vstate_raw'] = f"0x{vstate_value:08x}"
        payload['vstate_decoded'] = self._parse_vstate(vstate_value)
        
        self.offset += 8
        
        gps_count = self._read('<B', 1)
        
        gps_info_list = []
        for _ in range(gps_count if gps_count is not None else 0):
            gps_data = {}
            
            date_bytes = self.raw_bytes[self.offset : self.offset + 3]
            self.offset += 3
            time_bytes = self.raw_bytes[self.offset : self.offset + 3]
            self.offset += 3
            
            gps_data['date'] = f"{date_bytes[0]:02d}/{date_bytes[1]:02d}/20{date_bytes[2]:02d}"
            gps_data['time'] = f"{time_bytes[0]:02d}:{time_bytes[1]:02d}:{time_bytes[2]:02d}"

            lat_raw = self._read('<I', 4)
            lon_raw = self._read('<I', 4)
            
            # Converte para graus
            latitude = lat_raw / 3600000.0 if lat_raw is not None else 0
            longitude = lon_raw / 3600000.0 if lon_raw is not None else 0

            gps_data['speed_cm_s'] = self._read('<H', 2)
            direction_raw = self._read('<H', 2)
            gps_data['direction_degrees'] = direction_raw / 10.0 if direction_raw is not None else None
            flags_raw = self._read('<B', 1)
            gps_data['flags_raw'] = flags_raw

            # --- INÍCIO DA LÓGICA DE CORREÇÃO ---
            # Verifica o bit 0 para Longitude (0 = Oeste/Negativo)
            if not (flags_raw & 0b00000001):
                longitude *= -1
            
            # Verifica o bit 1 para Latitude (0 = Sul/Negativo)
            if not (flags_raw & 0b00000010):
                latitude *= -1
            
            gps_data['latitude'] = latitude
            gps_data['longitude'] = longitude
            # --- FIM DA LÓGICA DE CORREÇÃO ---
            
            gps_info_list.append(gps_data)

        payload['gps_info'] = gps_info_list
        
        # O resto do código permanece o mesmo
        final_offset = len(self.raw_bytes) - 4
        if self.offset < final_offset:
            self.offset = final_offset

        self.parsed_data['crc'] = f"0x{self._read('<H', 2):04x}"
        tail = self.raw_bytes[self.offset : self.offset + 2]
        self.parsed_data['protocol_tail'] = f"0x{tail.hex()}" if tail else "N/A"

        self.parsed_data['payload'] = payload

    def parse(self):
        # ... (este método permanece inalterado)
        header_bytes = self.raw_bytes[self.offset : self.offset + 2]
        self.offset += 2
        self.parsed_data['protocol_head'] = f"0x{header_bytes.hex()}"
        
        self.parsed_data['protocol_length'] = self._read('<H', 2)
        self.parsed_data['protocol_version'] = self._read('<B', 1)
        
        device_id_bytes = self.raw_bytes[self.offset : self.offset + 20]
        self.offset += 20
        self.parsed_data['device_id'] = device_id_bytes.decode('ascii', errors='ignore').strip('\x00')

        protocol_id = self._read('<H', 2)
        self.parsed_data['protocol_id'] = f"0x{protocol_id:04x}"

        if protocol_id == 0x0110:
            self._parse_login_packet()
        else:
            print(f"Parser para o Protocol ID 0x{protocol_id:04x} não implementado.")
            self.parsed_data['payload'] = f"Unparsed data starting at offset {self.offset}"

        return self.parsed_data

# --- Execução ---
raw_hex_packet = "40408600043231384c5341423230323530303030303200000010013bd6776861e3776832821500c3e00000983e0000950200020400032b2d441000811c011007191125227c3ece046466410900000e06bc42342e332e392e325f42524c20323032342d30312d323520303100442d3231384c53412d4220204844432d33365600000014360d0a"

parser = SinocastelParser(raw_hex_packet)
parsed_result = parser.parse()

print(json.dumps(parsed_result, indent=4))