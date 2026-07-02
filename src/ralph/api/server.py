from __future__ import annotations

from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from typing import Callable

from ralph.api.handlers import ApiHandlers, ApiResponse


@dataclass(frozen=True, slots=True)
class ApiServerConfig:
  enabled: bool = False
  host: str = "127.0.0.1"
  port: int = 8765

  @classmethod
  def from_mapping(cls, data: object) -> ApiServerConfig:
    if not isinstance(data, dict):
      raise ValueError("api must be a table")

    enabled = data.get("enabled", False)
    if not isinstance(enabled, bool):
      raise ValueError("api.enabled must be a boolean")

    host = data.get("host", "127.0.0.1")
    if not isinstance(host, str) or not host.strip():
      raise ValueError("api.host must be a non-empty string")

    port = data.get("port", 8765)
    if not isinstance(port, int) or port < 1 or port > 65535:
      raise ValueError("api.port must be an integer between 1 and 65535")

    return cls(enabled=enabled, host=host.strip(), port=port)

  def effective(self) -> ApiServerConfig:
    if not self.enabled:
      return ApiServerConfig(enabled=False)
    return ApiServerConfig(enabled=True, host=self.host, port=self.port)


class ApiServer:
  """Lightweight stdlib HTTP server for external integrations."""

  def __init__(self, config: ApiServerConfig, handler_factory: Callable[[], ApiHandlers]) -> None:
    self._config = config.effective()
    self._handler_factory = handler_factory
    self._server: ThreadingHTTPServer | None = None
    self._thread: threading.Thread | None = None

  @property
  def enabled(self) -> bool:
    return self._config.enabled

  def start(self) -> None:
    if not self._config.enabled:
      return

    handlers = self._handler_factory()

    class _Handler(BaseHTTPRequestHandler):
      def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

      def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

      def _dispatch(self, method: str) -> None:
        response = handlers.handle(method, self.path)
        self._write(response)

      def _write(self, response: ApiResponse) -> None:
        body = response.to_bytes()
        self.send_response(response.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

      def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    self._server = ThreadingHTTPServer((self._config.host, self._config.port), _Handler)
    self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
    self._thread.start()

  def stop(self) -> None:
    if self._server is not None:
      self._server.shutdown()
      self._server.server_close()
      self._server = None
    if self._thread is not None:
      self._thread.join(timeout=2.0)
      self._thread = None
