import socket

PACOTE_HEXADECIMAL = "40408600043231384c534142323032353030303030320000001001508e7a68ed977a68fea31900459200002b48000029010402040003382d441500831c0112071912341e40b6ec044ca84d09f6098a07ec42342e332e392e325f42524c20323032342d30312d323520303100442d3231384c53412d4220204844432d333656000000ed6d0d0a"

HOST, PORT = "localhost", 29479

dados_para_enviar = bytes.fromhex(PACOTE_HEXADECIMAL)

try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        
        sock.sendall(dados_para_enviar)
        print("✅ Pacote de dados enviado com sucesso para o servidor!")
        resposta = sock.recv(1024)
        print(resposta)

except ConnectionRefusedError:
    print("❌ Erro: Não foi possível conectar ao servidor. Verifique se o 'obd_server.py' está rodando.")
except Exception as e:
    print(f"Ocorreu um erro: {e}")