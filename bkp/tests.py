import asyncio

async def server(message):
    reader, writer = await asyncio.open_connection('127.0.0.1', 8888)

    print (f'Enviando: {message!r}')
    writer.write(message.encode())
    await writer.drain()

    data = await reader.read(100)
    print(f'Recebido: {data.decode()!r}')

    print('Fechando conexão')
    writer.close()
    await writer.wait_closed()

asyncio.run(server('Hello World!'))