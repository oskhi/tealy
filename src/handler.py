class Handler:
    """Parses input and handles commands."""

    def unknown(self, session: object, command: str) -> None:
        session.send_message(f"Unknown command: '{command}'\r\n")
        session.send_message(f"See a list of commands with '/help'\r\n")

    def handle(self, session: object, line: str) -> None:
        line = line.strip()
        
        if not line:
            return

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

