"""Mock TCP server that stands in for a real external sensor.

It can be driven to send well-formed protocol lines (acquisition trigger and
position lines) as well as intentionally malformed / incorrect data, so tests
can exercise both the happy path and the error-handling paths of
``SensorFunctions.startSensor``.
"""

import socket
import threading


class MockExternalSensorServer:
    """A minimal TCP server simulating the external sensor hardware.

    Usage:
        server = MockExternalSensorServer()
        server.start()
        ...connect a client to (server.host, server.port)...
        server.send_line("123")                       # acquisition trigger
        server.send_line("123,1,100.0,200.0,0.0,0,1.0,0.0,0.0,0.0,0.0,0.0,2")
        server.send_raw("not-a-valid-line-at-all\n")   # incorrect data format
        server.stop()
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        self.host = host
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((host, port))
        self._server_socket.listen(1)
        self.port = self._server_socket.getsockname()[1]

        self._accept_thread: "threading.Thread | None" = None
        self._client_conn: "socket.socket | None" = None
        self._client_ready = threading.Event()
        self._stopped = False

    def start(self) -> None:
        # Accept a single client connection in the background so the calling
        # test can connect a real socket to (self.host, self.port).
        self._accept_thread = threading.Thread(target=self._accept, daemon=True)
        self._accept_thread.start()

    def _accept(self) -> None:
        try:
            conn, _addr = self._server_socket.accept()
            self._client_conn = conn
            self._client_ready.set()
        except OSError:
            pass

    def wait_for_client(self, timeout: float = 5.0) -> bool:
        return self._client_ready.wait(timeout)

    def send_raw(self, data: str) -> None:
        # Send arbitrary bytes as-is; used to simulate malformed/incorrect
        # data coming from a misbehaving sensor.
        if not self.wait_for_client():
            raise RuntimeError("No client connected to mock sensor server")
        assert self._client_conn is not None
        self._client_conn.sendall(data.encode("utf-8"))

    def send_line(self, line: str) -> None:
        # Send one well-formed protocol line terminated with CRLF.
        self.send_raw(line + "\r\n")

    def send_acquisition_trigger(self, acq_no) -> None:
        self.send_line(str(acq_no))

    def send_position_line(self, acq_no, objects: list) -> None:
        # objects: list of dicts with keys X, Y, RZ, Tag, Score, Val1..Val5, Level
        fields = [str(acq_no), str(len(objects))]
        for obj in objects:
            fields.extend(
                str(obj[key])
                for key in ("X", "Y", "RZ", "Tag", "Score", "Val1", "Val2", "Val3", "Val4", "Val5", "Level")
            )
        self.send_line(",".join(fields))

    def send_incorrect_data(self, payload: str) -> None:
        # Explicit helper to simulate an external sensor sending an incorrect
        # data format (garbage text, wrong field count, non-numeric values...).
        self.send_raw(payload if payload.endswith(("\n", "\r")) else payload + "\r\n")

    def disconnect_client(self) -> None:
        if self._client_conn is not None:
            try:
                self._client_conn.close()
            except OSError:
                pass
            self._client_conn = None
            self._client_ready.clear()

    def stop(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        self.disconnect_client()
        try:
            self._server_socket.close()
        except OSError:
            pass
        if self._accept_thread is not None:
            self._accept_thread.join(timeout=2)
