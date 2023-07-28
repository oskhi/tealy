import asyncio
import configparser
import logging
import os.path
import time

config = configparser.ConfigParser()
config.read(os.path.dirname(__file__) + '/config.ini')

HOST = config['config']['host']
PORT = config['config']['port']
NAME = config['config']['name']

HELP_MSG = """
Available commands:
   
/look     - Display users currently in this room
/who      - Display users currently logged in
/logout   - Log out and enter to Lobby
/quit     - Close the connection
"""

logging.basicConfig(level=logging.DEBUG)


class Handler:
    """Parses input and handles commands."""

    def unknown(self, session: object, command: str) -> None:
        session.send_message(f"Unknown command: '{command}'\r\n")
        session.send_message(f"See a list of commands with '/help'\r\n")

    def handle(self, session: object, line: str) -> None:
        if not line.strip():
            return
        line = line.strip()

        if line[0] != '/':
            command = "say"
            method = getattr(self, command, None)
            method(session, line)

        else:
            parts = line.split(' ')
            command = parts[0][1:]

            try:
                args = (i.strip() for i in parts[1:])
            except IndexError:
                args = ''

            method = getattr(self, command, None)

            try:
                method(session, *args)
            except TypeError:
                self.unknown(session, command)


class Room(Handler):
    """The base class for all room objects."""

    def __init__(self, server: object) -> None:
        self.server = server
        self.sessions = {}

    def broadcast(self, message: str, subject: object = None) -> None:
        tg = list(self.sessions.values())

        if subject:
            tg.remove(subject)

        message = f"[{time.strftime('%X')}] {message}".encode()

        for i in tg:
            # Each iteration writes some data 
            # into the sessions transport buffer
            i.transport.write(message)

    def add(self, session: object) -> None:
        self.sessions[session.name] = session
        self.broadcast(f"{session.name} has entered the room.\r\n")

    def remove(self, session: object) -> None:
        try:
            del self.sessions[session.name]
        except Exception as e:
            logging.info(e)

        self.broadcast(f"{session.name} has left the room.\r\n")

    def quit(self, session: object) -> None:
        self.remove(session)
        try:
            del self.server.users[session.name]
        finally:
            session.close_connection()


class Lounge(Room):
    """
    The main chat room object. Provides methods for
    user commands.
    """

    def say(self, session: object, line: str) -> None:
        self.broadcast(f"<{session.name}> {line}\r\n", session)

    def help(self, session: object) -> None:
        message = HELP_MSG.lstrip()
        session.send_message(message)

    def look(self, session: object) -> None:
        session.send_message("The following are in this room:\r\n")

        for name in self.sessions:
            session.send_message(name + "\r\n")

    def who(self, session: object) -> None:
        session.send_message("The following are logged in:\r\n")

        for name in self.server.users:
            session.send_message(name + "\r\n")

    def logout(self, session: object) -> None:
        del self.server.users[session.name]
        self.remove(session)
        session.enter_room(Lobby(self.server))


class Lobby(Room):
    """
    A room for users to log in. Forwards
    logged-in users to Lounge.
    """

    def add(self, session: object) -> None:
        session.send_message(
            """ * Welcome to {} * \n\nUse '/login <name>' to log in\r\n"""
            .format(self.server.name))

    def unknown(self, session: object, command: str) -> None:
        session.send_message("Use '/login <name>' to log in.\r\n")

    def login(self, session: object, line: str) -> None:
        name = line.strip()

        if not name:
            session.send_message("Please enter a name.\r\n")
        elif name in self.server.users:
            session.send_message(f"The name '{name}' is taken.\r\n")
            session.send_message("Please try again.\r\n")
        else:
            session.name = name
            self.server.users[session.name] = session
            session.enter_room(self.server.main_room)


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
            current.remove(self)

        self.room = room
        room.add(self)

    def connection_made(self, transport: object) -> None:
        self.transport = transport
        self.peername = transport.get_extra_info('peername')

        logging.info(f"{self.peername} connected.")
        self.enter_room(Lobby(self.server))

    def connection_lost(self, exc: Exception) -> None:
        logging.info(f"{self.peername} disconnected.")
        if exc: logging.info(exc)

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

    def __init__(self, host: str, port: int, name: str) -> None:
        self.host = host
        self.port = port
        self.name = name
        self.users = {}
        self.main_room = Lounge(self)

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
    s = ChatServer(HOST, int(PORT), NAME)
    try:
        asyncio.run(s.main())
    except KeyboardInterrupt:
        pass
