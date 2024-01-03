from constants import *
from handler import Handler

import time


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
            i.transport.write(message)

    def add(self, session: object) -> None:
        self.sessions[session.name] = session
        self.broadcast(f"{session.name} has entered the room.\r\n")

    def remove(self, session: object) -> None:
        try:
            del self.sessions[session.name]
        except Exception as e:
            logging.info(e)
            raise

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
        message = HELP_MSG.lstrip() + '\n'
        session.send_message(message)

    def look(self, session: object) -> None:
        session.send_message("The following users are in this room:\r\n")

        for name in self.sessions:
            session.send_message(name + "\r\n")

    def who(self, session: object) -> None:
        session.send_message("The following users are logged in:\r\n")

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
            session.enter_room(self.server.lounge)

