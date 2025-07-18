import socketserver
import json
import struct
from datetime import datetime, timedelta

# ==============================================================================
# CLASSE DO PARSER (DECODIFICADOR) - Refinada na nossa conversa anterior
# ==============================================================================
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

    def _unix_to_datetime(self, unix_timestamp):
        if unix_timestamp is None: return None
        return datetime(2000, 1, 1) + timedelta(seconds=unix_timestamp)

    def _parse_login_packet(self):
        payload = {}
        
        last_acc_on_ts = self._read('I', 4)
        utc_time_ts = self._read('I', 4)
        payload['utc_time'] = self._unix_to_datetime(utc_time_ts).strftime('%Y-%m-%d %H:%M:%S') if utc_time_ts else None
        
        # Lógica de Sincronização do Odômetro
        device_mileage_meters = self._read('I', 4)
        device_mileage_km = (device_mileage_meters / 1000.0) if device_mileage_meters is not None else 0
        calculated_odometer_km = self.base_odometer_km + device_mileage_km
        
        payload['device_reported_mileage_km'] = round(device_mileage_km, 2)
        payload['calculated_vehicle_odometer_km'] = round(calculated_odometer_km, 2)
        
        # Restante dos campos do payload
        # (Para manter o código conciso, omitimos os outros campos aqui, 
        # mas você pode adicioná-los seguindo o modelo anterior)
        
        print(f"Dados decodificados do Dispositivo {self.parsed_data.get('device_id')}:")
        print(json.dumps(self.parsed_data, indent=4))
        
        self.parsed_data['payload'] = payload

    def parse(self):
        if not self.raw_bytes or len(self.raw_bytes) < 28:
             print("Pacote recebido muito curto ou inválido.")
             return None

        self.parsed_data['protocol_head'] = f"0x{self.raw_bytes[self.offset:self.offset+2].hex()}"
        self.offset += 2
        self.parsed_data['protocol_length'] = self._read('H', 2)
        self.parsed_data['protocol_version'] = self._read('B', 1)
        device_id_bytes = self.raw_bytes[self.offset : self.offset + 20]
        self.offset += 20
        self.parsed_data['device_id'] = device_id_bytes.decode('ascii', errors='ignore').strip('\x00')
        protocol_id = self._read('H', 2)
        self.parsed_data['protocol_id'] = f"0x{protocol_id:04x}" if protocol_id is not None else None

        if protocol_id == 0x0110: # Protocolo de Login
            self._parse_login_packet()
        else:
            print(f"Protocolo 0x{protocol_id:04x} recebido, mas não há parser implementado.")

        return self.parsed_data

# ==============================================================================
# CLASSE DO SERVIDOR TCP
# ==============================================================================
class TCPHandler(socketserver.BaseRequestHandler):
    """
    O Handler que processa cada conexão.
    Uma nova instância desta classe é criada para cada veículo que se conecta.
    """
    def handle(self):
        print(f"\nNova conexão recebida de: {self.client_address[0]}")
        try:
            while True:
                # Recebe os dados em blocos de 1024 bytes
                data = self.request.recv(1024)
                if not data:
                    print(f"Conexão fechada por: {self.client_address[0]}")
                    break
                
                # Os dados chegam em bytes, convertemos para uma string hexadecimal
                hex_data = data.hex()
                print(f"Recebido {len(data)} bytes (payload hex): {hex_data}")
                
                # --- AQUI A MÁGICA ACONTECE ---
                # Aqui você buscaria o odômetro base do seu banco de dados
                # para o dispositivo que se conectou. Usaremos um valor fixo para o exemplo.
                # Exemplo: O carro com o painel da foto
                base_odometer_for_this_device = 105826.41

                # Cria uma instância do parser e decodifica o pacote
                parser = SinocastelParser(hex_data, base_odometer_km=base_odometer_for_this_device)
                parsed_data = parser.parse()

                # No futuro, em vez de imprimir, você salvaria `parsed_data` no seu banco de dados.

        except Exception as e:
            print(f"Ocorreu um erro na conexão com {self.client_address[0]}: {e}")

# ==============================================================================
# EXECUÇÃO PRINCIPAL DO SERVIDOR
# ==============================================================================
if __name__ == "__main__":
    # Configure o HOST e a PORTA
    # Use '0.0.0.0' para escutar em todas as interfaces de rede disponíveis
    HOST, PORT = "0.0.0.0", 29479 

    print(f"Servidor de Escuta OBD iniciado em {HOST}:{PORT}")
    print("Aguardando conexões dos veículos...")

    # Usamos ThreadingTCPServer para lidar com múltiplas conexões simultaneamente
    with socketserver.ThreadingTCPServer((HOST, PORT), TCPHandler) as server:
        # Mantém o servidor rodando para sempre
        server.serve_forever()