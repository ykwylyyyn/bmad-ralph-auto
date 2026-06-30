from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json
import socket
from typing import Callable

from ralph.common.protocol import Request, Response

from .runtime import RuntimePaths


def socket_supported() -> bool:
    return hasattr(socket, "AF_UNIX")


class IpcServer:
    def __init__(self, paths: RuntimePaths):
        self.paths = paths
        self._socket: socket.socket | None = None

    def start(self) -> None:
        self.paths.ensure()
        if socket_supported():
            try:
                self.paths.socket_file.unlink()
            except FileNotFoundError:
                pass
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(str(self.paths.socket_file))
        else:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.bind(("127.0.0.1", 0))
            host, port = server.getsockname()
            self.paths.port_file.write_text(f"{host}:{port}", encoding="utf-8")
        server.listen(8)
        server.setblocking(False)
        self._socket = server

    def poll(self, handler: Callable[[Request], Response]) -> bool:
        if self._socket is None:
            return False
        handled_stop = False
        while True:
            try:
                connection, _address = self._socket.accept()
            except BlockingIOError:
                break
            with connection:
                connection.settimeout(1)
                request = _read_request(connection)
                response = handler(request)
                handled_stop = handled_stop or request.type == "stop"
                connection.sendall((json.dumps(response.to_json_dict()) + "\n").encode("utf-8"))
        return handled_stop

    def close(self) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        try:
            self.paths.socket_file.unlink()
        except FileNotFoundError:
            pass
        try:
            self.paths.port_file.unlink()
        except FileNotFoundError:
            pass


def request_daemon(paths: RuntimePaths, request: Request, timeout_secs: float = 2.0) -> Response:
    if socket_supported():
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        address: str | tuple[str, int] = str(paths.socket_file)
    else:
        if not paths.port_file.exists():
            return Response(type="error", message="daemon socket is not available")
        host, port = paths.port_file.read_text(encoding="utf-8").strip().split(":", 1)
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        address = (host, int(port))
    client.settimeout(timeout_secs)
    try:
        client.connect(address)
        client.sendall((json.dumps(request.to_json_dict()) + "\n").encode("utf-8"))
        response = _read_json_line(client)
    finally:
        client.close()
    return Response(
        type=response.get("type", "error"),
        message=response.get("message", ""),
        data=response.get("data"),
    )


def status_response(status: object) -> Response:
    if not is_dataclass(status):
        return Response(type="error", message="invalid status")
    return Response(type="ok", message=status.state, data=asdict(status))


def _read_request(connection: socket.socket) -> Request:
    data = _read_json_line(connection)
    return Request(
        type=data.get("type"),
        story_id=data.get("story_id"),
        graceful=data.get("graceful"),
    )


def _read_json_line(connection: socket.socket) -> dict[str, object]:
    chunks: list[bytes] = []
    while True:
        chunk = connection.recv(4096)
        if not chunk:
            break
        chunks.append(chunk)
        if b"\n" in chunk:
            break
    raw = b"".join(chunks).split(b"\n", 1)[0]
    return json.loads(raw.decode("utf-8"))
