# Projeto OBD WebSocket Server

## 🎯 Objetivo
Desenvolver uma aplicação web baseada em WebSocket, que escute a porta 29479 e processe dados recebidos de um dispositivo OBD. O sistema registra os dados brutos, converte para hexadecimal e interpreta conforme o protocolo do fabricante (inicialmente protocolo 1001).

## 📦 Estrutura do Projeto
- `ws_server.py`: Servidor WebSocket principal.
- `decoder_1001.py`: Decoder modular para protocolo 1001.
- `documentacao/`: Documentos e arquivos de referência dos protocolos.
- `bkp/`: Backup dos códigos antigos.
- `logs/`: Logs de dados brutos e interpretações.

## 🚀 Como Executar
1. Instale as dependências:
   ```bash
   pip install websockets
   ```
2. Execute o servidor:
   ```bash
   python ws_server.py
   ```
3. O servidor escutará na porta 29479. Conecte um cliente WebSocket e envie dados para teste.

## 🧩 Modularidade
- O sistema foi projetado para fácil expansão de novos protocolos.
- Para adicionar um novo protocolo, crie um novo decoder e registre no dicionário `decoders` em `ws_server.py`.

## 📝 Logs
- Todos os dados brutos recebidos são registrados em `logs/raw_data.log`.
- As interpretações do protocolo 1001 são registradas em `logs/interpreted_1001.log`.

## ⚙️ Configurações
- Suporte planejado para arquivos `.cursor` e `.mcp`.
- Adicione arquivos de configuração na raiz do projeto conforme necessário.

## 📚 Documentação
- Consulte a pasta `documentacao/` para manuais, protocolos e arquivos de referência.

## 🧹 Limpeza
- Todos os arquivos `.py` e `.ts` antigos foram movidos para `bkp/`.

## 👨‍💻 Expansão
- O sistema está pronto para receber novos decoders e protocolos.
- Basta implementar um novo decoder e integrá-lo ao servidor.

---

Desenvolvido para ser escalável, modular e de fácil manutenção. 