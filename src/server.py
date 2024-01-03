from rooms import *

import asyncio
import configparser
import logging
import os.path

config = configparser.ConfigParser()
config.read(os.path.dirname(__file__) + '/config.ini')

HOST = config['config']['host']
PORT = config['config']['port']
NAME = config['config']['name']

logging.basicConfig(level=logging.DEBUG)


class ChatServerProtocol(asyncio.Protocol):
    """
    Provides methods for communication with the client.
    Forwards the client to Lobby when a connection is made.
    """

    def __init__(self, server: object) -> None:
        self.server = server
        self.terminator = '\r\n'
        self.data = []
        self.name = None

    def enter_room(self, room: object) -> None:
        try:
            current = self.room
        except AttributeError:
            pass
        else:
            try:
                current.remove(self)
            except Exception as e:
                logging.info(e)

        self.room = room
        room.add(self)

    def connection_made(self, transport: object) -> None:
        self.transport = transport
        self.peername = transport.get_extra_info('peername')

        logging.info(f"{self.peername} connected.")
        self.enter_room(Lobby(self.server))

    def connection_lost(self, exc: Exception) -> None:
        logging.info(f"{self.peername} disconnected.")

        try:
            self.room.remove(self)
        except Exception as e:
            logging.info(e)

        if exc: 
            logging.info(exc)

    def data_received(self, data: bytes) -> None:
        data = data.decode()
        self.data.append(data)

        if self.terminator in data:
            line = ''.join(data)
            
            try:
                self.room.handle(self, line)
            except Exception as e:
                logging.info(e)

    def send_message(self, message: str) -> None:
        self.transport.write(message.encode())

    def eof_received(self) -> None:
        logging.info(f"EOF received from {self.peername}.")
        self.transport.close()

    def close_connection(self) -> None:
        self.transport.close()


class ChatServer:
    """
    Spawns a ChatServerProtocol object for each client. Keeps information
    about the currently logged-in users on the server.
    """

    def __init__(self, host: str, port: str, name: str) -> None:
        self.host = host
        self.port = int(port)
        self.name = name
        self.users = {}
        self.lounge = Lounge(self)

    async def main(self) -> None:
        loop = asyncio.get_running_loop()
        server = await loop.create_server(
            lambda: ChatServerProtocol(self),
            self.host, self.port)

        logging.info("Server running on {}".format(
            server.sockets[0].getsockname()))

        async with server:
            await server.serve_forever()


if __name__ == '__main__':
    s = ChatServer(HOST, PORT, NAME)

    try:
        asyncio.run(s.main())
    except KeyboardInterrupt:
        pass

