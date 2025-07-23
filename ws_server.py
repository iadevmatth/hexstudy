import asyncio
import websockets
import logging
from datetime import datetime
from pathlib import Path
from decoder_1001 import Decoder1001

# Configuração de logging
log_dir = Path('logs')
log_dir.mkdir(exist_ok=True)
raw_log_file = log_dir / 'raw_data.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    handlers=[
        logging.FileHandler(raw_log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Placeholder para decodificadores de protocolo
class ProtocolDecoder:
    def decode(self, data: bytes) -> dict:
        # Implementação futura para múltiplos protocolos
        return {"hex": data.hex(), "raw": data}

decoders = {
    '1001': Decoder1001(),
}

def get_decoder(protocol_id: str):
    return decoders.get(protocol_id, ProtocolDecoder())

async def handler(websocket, path):
    logging.info(f'Nova conexão: {websocket.remote_address}')
    async for message in websocket:
        now = datetime.now().isoformat()
        # Registro do dado bruto
        logging.info(f'RAW: {message}')
        # Exemplo de uso do decoder 1001
        decoder = get_decoder('1001')
        decoded = decoder.decode(message.encode() if isinstance(message, str) else message)
        logging.info(f'DECODED: {decoded}')

async def main():
    async with websockets.serve(handler, "0.0.0.0", 29479):
        print("Servidor WebSocket escutando na porta 29479...")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main()) 