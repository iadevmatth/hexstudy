import socketserver
import json
import struct
import requests
from datetime import datetime, timedelta

class SinocastelParser:
    def __init__(self, raw_hex_data, base_odometer_km=0):
        self.raw_bytes = bytes.fromhex(raw_hex_data)
        self.parsed_data = {}
        self.offset = 0
        self.base_odometer_km = base_odometer_km

    def _read(self, fmt, size):
        try:
            # Unpack dos dados usando o formato little-endian '<'
            value = struct.unpack(f'<{fmt}', self.raw_bytes[self.offset : self.offset + size])[0]
            self.offset += size
            return value
        except (struct.error, IndexError):
            return None

    def _read_fixed_string(self, size):
        """Lê uma string de tamanho fixo e remove o preenchimento nulo."""
        value_bytes = self.raw_bytes[self.offset : self.offset + size]
        self.offset += size
        return value_bytes.decode('ascii', errors='ignore').strip('\x00')

    def _read_variable_string(self):
        """Lê uma string terminada pelo caractere nulo."""
        end_index = self.raw_bytes.find(b'\x00', self.offset)
        if end_index == -1:
            return None
        value = self.raw_bytes[self.offset:end_index].decode('ascii', errors='ignore')
        self.offset = end_index + 1
        return value

    def _unix_to_datetime(self, unix_timestamp):
        """Converte o timestamp do protocolo (epoch em 2000-01-01) para um formato legível."""
        if unix_timestamp is None or unix_timestamp == 0:
            return None
        try:
            return (datetime(2000, 1, 1) + timedelta(seconds=unix_timestamp)).strftime('%Y-%m-%d %H:%M:%S')
        except:
            return "Invalid Timestamp"

    def _parse_vstate(self, vstate_value):
        """Decodifica o bitmask de status do veículo."""
        if vstate_value is None:
            return None
        states = []
        if (vstate_value & 0x00040000):
            states.append("ACC ON") # Ignição ligada
        # Outras flags de status podem ser adicionadas aqui
        return ", ".join(states) if states else "Normal"
        
    def _parse_login_packet(self):
        
        payload = {}
        
        # Timestamps
        payload['last_accon_time'] = self._unix_to_datetime(self._read('I', 4))
        payload['utc_time'] = self._unix_to_datetime(self._read('I', 4))
        
        # Odômetro e Quilometragem
        device_mileage_meters = self._read('I', 4)
        device_mileage_km = (device_mileage_meters / 1000.0) if device_mileage_meters is not None else 0
        payload['calculated_vehicle_odometer_km'] = round(self.base_odometer_km + device_mileage_km, 2)
        
        current_trip_meters = self._read('I', 4)
        payload['current_trip_km'] = round(current_trip_meters / 1000.0, 2) if current_trip_meters is not None else 0

        # Combustível
        payload['total_fuel_liters'] = round(self._read('I', 4) / 100.0, 2)
        payload['current_fuel_liters'] = round(self._read('H', 2) / 100.0, 2)

        # Status do Veículo
        vstate_value = self._read('I', 4)
        payload['vehicle_status'] = self._parse_vstate(vstate_value)
        
        # Informações do Bloco "Reservado"
        reserved_block = self.raw_bytes[self.offset:self.offset+8]; self.offset += 8
        payload['vehicle_voltage'] = round((reserved_block[1] * 0.1), 2) if len(reserved_block) > 1 else None
        payload['cellular_signal_strength'] = reserved_block[4] if len(reserved_block) > 4 else None

        # GPS
        gps_count = self._read('B', 1)
        if gps_count and gps_count > 0:
            
            gps_data = {}
            date_bytes = self.raw_bytes[self.offset : self.offset + 3]; self.offset += 3
            time_bytes = self.raw_bytes[self.offset : self.offset + 3]; self.offset += 3
            gps_data['date_time'] = f"20{date_bytes[2]:02d}-{date_bytes[1]:02d}-{date_bytes[0]:02d} {time_bytes[0]:02d}:{time_bytes[1]:02d}:{time_bytes[2]:02d}"
            lat_raw = self._read('I', 4); lon_raw = self._read('I', 4)
            latitude = lat_raw / 3600000.0 if lat_raw is not None else 0
            longitude = lon_raw / 3600000.0 if lon_raw is not None else 0
            gps_data['speed_kph'] = round(self._read('H', 2) * 0.036, 2)
            gps_data['direction_degrees'] = self._read('H', 2) / 10.0
            flags_raw = self._read('B', 1)
            if flags_raw is not None:
                if not (flags_raw & 0b00000001): longitude *= -1 # Bit 0: 0=Oeste, 1=Leste
                if not (flags_raw & 0b00000010): latitude *= -1  # Bit 1: 0=Sul, 1=Norte
                gps_data['satellites'] = flags_raw >> 4
                gps_data['fixed'] = "3D" if (flags_raw & 0b00001100) else "2D/No Fix"
            gps_data['latitude'] = round(latitude, 6)
            gps_data['longitude'] = round(longitude, 6)
            payload['gps_info'] = gps_data

        payload['software_version'] = self._read_variable_string()
        payload['hardware_version'] = self._read_variable_string()

        self.parsed_data['payload'] = payload

    def parse(self):
        
        if not self.raw_bytes or len(self.raw_bytes) < 28:
            return {"error": "Pacote de dados inválido ou muito curto."}

        self.parsed_data['protocol_head'] = f"0x{self.raw_bytes[self.offset:self.offset+2].hex()}"
        self.offset += 2
        self.parsed_data['protocol_length'] = self._read('H', 2)
        self.parsed_data['protocol_version'] = self._read('B', 1)
        self.parsed_data['device_id'] = self._read_fixed_string(20)
        protocol_id = self._read('H', 2)
        self.parsed_data['protocol_id'] = f"0x{protocol_id:04x}" if protocol_id is not None else None

        if protocol_id == 0x0110:
            self._parse_login_packet()
        else:
            self.parsed_data['error'] = f"Parser para o Protocol ID 0x{protocol_id:04x} não implementado."
        
        return self.parsed_data

class TCPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        print(f"\n[+] Nova conexão de: {self.client_address[0]}")
        try:
            while True:
                data = self.request.recv(1024)
                if not data:
                    print(f"[-] Conexão fechada por: {self.client_address[0]}")
                    break
                
                hex_data = data.hex()
                print(f"[*] Recebido {len(data)} bytes de {self.client_address[0]}")
                
                # Em um sistema real, o 'base_odometer_km' viria de um banco de dados
                # associado ao ID do dispositivo que se conectou.
                base_odometer_for_this_device = 105826.41

                parser = SinocastelParser(hex_data, base_odometer_km=base_odometer_for_this_device)
                parsed_data = parser.parse()

                print("--- DADOS DECODIFICADOS ---")
                print(json.dumps(parsed_data, indent=4))
                print("---------------------------\n")

        except Exception as e:
            print(f"[!] Erro na conexão com {self.client_address[0]}: {e}")

if __name__ == "__main__":
    HOST, PORT = "0.0.0.0", 29479 

    print("==============================================")
    print(f"   Servidor de Escuta OBD Iniciado")
    print(f"   Escutando em: {HOST}:{PORT}")
    print("==============================================")
    print("Aguardando conexões dos veículos...")

    with socketserver.ThreadingTCPServer((HOST, PORT), TCPHandler) as server:
        server.serve_forever()