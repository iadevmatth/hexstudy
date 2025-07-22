import struct
import json
from datetime import datetime, timedelta

class SinocastelParser:
    # 1. Adicionamos o 'base_odometer_km' ao construtor
    def __init__(self, raw_hex_data, base_odometer_km=0):
        """
        Inicializa o parser.

        :param raw_hex_data: O pacote de dados hexadecimal.
        :param base_odometer_km: A quilometragem do painel do carro no momento da 
                                 instalação do dispositivo.
        """
        self.raw_bytes = bytes.fromhex(raw_hex_data)
        self.parsed_data = {}
        self.offset = 0
        # Armazena o odômetro base para uso posterior
        self.base_odometer_km = base_odometer_km

    def _read(self, fmt, size):
        try:
            value = struct.unpack(f'<{fmt}', self.raw_bytes[self.offset : self.offset + size])[0]
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
        
    def _unix_to_datetime(self, unix_timestamp):
        if unix_timestamp is None:
            return None
        # O protocolo usa um epoch diferente, ajustado para UTC+0
        # A data base do protocolo é 2000-01-01
        return datetime(2000, 1, 1) + timedelta(seconds=unix_timestamp)

    def _parse_login_packet(self):
        payload = {}
        
        # Leitura dos campos de tempo (timestamps Unix)
        last_acc_on_ts = self._read('I', 4)
        utc_time_ts = self._read('I', 4)

        payload['last_accon_time'] = self._unix_to_datetime(last_acc_on_ts).strftime('%Y-%m-%d %H:%M:%S') if last_acc_on_ts else None
        payload['utc_time'] = self._unix_to_datetime(utc_time_ts).strftime('%Y-%m-%d %H:%M:%S') if utc_time_ts else None
        
        # --- LÓGICA DE SINCRONIZAÇÃO DO ODÔMETRO ---
        # 2. Implementamos o cálculo aqui

        # Lê a quilometragem reportada pelo dispositivo (em metros)
        device_mileage_meters = self._read('I', 4)
        payload['device_reported_mileage_meters'] = device_mileage_meters
        
        # Converte a quilometragem do dispositivo para KM
        device_mileage_km = (device_mileage_meters / 1000.0) if device_mileage_meters is not None else 0
        payload['device_reported_mileage_km'] = round(device_mileage_km, 2)

        # Calcula o odômetro real do veículo somando o base com o do dispositivo
        calculated_odometer_km = self.base_odometer_km + device_mileage_km
        payload['calculated_vehicle_odometer_km'] = round(calculated_odometer_km, 2)
        
        # --- FIM DA LÓGICA DE SINCRONIZAÇÃO ---

        payload['current_trip_mileage'] = self._read('I', 4)
        payload['total_fuel'] = self._read('I', 4)
        payload['current_fuel'] = self._read('H', 2)
        
        vstate_value = self._read('I', 4)
        payload['vstate_raw'] = f"0x{vstate_value:08x}" if vstate_value is not None else None
        payload['vstate_decoded'] = self._parse_vstate(vstate_value) if vstate_value is not None else None
        
        self.offset += 8 # Pula o campo 'reservado' de 8 bytes
        
        gps_count = self._read('B', 1)
        gps_info_list = []
        for _ in range(gps_count if gps_count is not None else 0):
            # A lógica de parse do GPS permanece a mesma
            gps_data = {}
            date_bytes = self.raw_bytes[self.offset : self.offset + 3]; self.offset += 3
            time_bytes = self.raw_bytes[self.offset : self.offset + 3]; self.offset += 3
            gps_data['date'] = f"{date_bytes[0]:02d}/{date_bytes[1]:02d}/20{date_bytes[2]:02d}"
            gps_data['time'] = f"{time_bytes[0]:02d}:{time_bytes[1]:02d}:{time_bytes[2]:02d}"
            lat_raw = self._read('I', 4)
            lon_raw = self._read('I', 4)
            latitude = lat_raw / 3600000.0 if lat_raw is not None else 0
            longitude = lon_raw / 3600000.0 if lon_raw is not None else 0
            gps_data['speed_cm_s'] = self._read('H', 2)
            direction_raw = self._read('H', 2)
            gps_data['direction_degrees'] = direction_raw / 10.0 if direction_raw is not None else None
            flags_raw = self._read('B', 1)
            if flags_raw is not None:
                if not (flags_raw & 0b00000001): longitude *= -1
                if not (flags_raw & 0b00000010): latitude *= -1
            gps_data['latitude'] = latitude
            gps_data['longitude'] = longitude
            gps_info_list.append(gps_data)

        payload['gps_info'] = gps_info_list
        self.parsed_data['payload'] = payload

    def parse(self):
        self.parsed_data['protocol_head'] = f"0x{self.raw_bytes[self.offset:self.offset+2].hex()}"
        self.offset += 2
        self.parsed_data['protocol_length'] = self._read('H', 2)
        self.parsed_data['protocol_version'] = self._read('B', 1)
        device_id_bytes = self.raw_bytes[self.offset : self.offset + 20]
        self.offset += 20
        self.parsed_data['device_id'] = device_id_bytes.decode('ascii', errors='ignore').strip('\x00')
        protocol_id = self._read('H', 2)
        self.parsed_data['protocol_id'] = f"0x{protocol_id:04x}" if protocol_id is not None else None

        # O Protocol ID correto, lido em little-endian, é 0x0110
        if protocol_id == 0x0110:
            self._parse_login_packet()
        else:
            self.parsed_data['payload'] = f"Parser para o Protocol ID 0x{protocol_id:04x} não implementado."

        # Pula para o final para ler o CRC e a cauda
        # Isso evita erros caso haja campos não mapeados no meio do payload
        final_offset = len(self.raw_bytes) - 4
        if self.offset < final_offset:
            self.offset = final_offset

        self.parsed_data['crc'] = f"0x{self._read('H', 2):04x}"
        self.parsed_data['protocol_tail'] = f"0x{self.raw_bytes[self.offset:self.offset+2].hex()}"

        return self.parsed_data

# --- COMO USAR O CÓDIGO MODIFICADO ---

# O mesmo pacote hexadecimal de antes
raw_hex_packet = "40408600043231384c534142323032353030303030320000001001508e7a68ed977a68fea31900459200002b48000029010402040003382d441500831c0112071912341e40b6ec044ca84d09f6098a07ec42342e332e392e325f42524c20323032342d30312d323520303100442d3231384c53412d4220204844432d333656000000ed6d0d0a"

# 3. Vamos calcular o odômetro base para o exemplo
# Odômetro do Painel: 107.236 km
# Odômetro do Dispositivo: 1.409,586 km
# Base = 107236 - 1409.586 = 105826.414 km
odometro_base_do_veiculo = 105826.41

# Inicializa o parser passando o odômetro base
parser = SinocastelParser(raw_hex_packet, base_odometer_km=odometro_base_do_veiculo)
parsed_result = parser.parse()

print(json.dumps(parsed_result, indent=4))