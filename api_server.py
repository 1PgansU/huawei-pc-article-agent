"""Serve the five-page frontend and the domain API on localhost."""
from __future__ import annotations

import json
import mimetypes
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from agent.service import IntegrationService, ServiceError

ROOT = Path(__file__).resolve().parent
SERVICE = IntegrationService()


class ApiHandler(SimpleHTTPRequestHandler):
    """Expose only frontend static files and explicitly registered API assets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "frontend"), **kwargs)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        # Keep successful responses on the documented envelope while preserving error DTOs.
        if status < 400 and "error" not in payload:
            payload = {"data": payload, "request_id": uuid4().hex}
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def _error(self, exc: Exception) -> None:
        if isinstance(exc, ServiceError):
            self._send_json({"error": {"code": exc.code, "message": str(exc), "retryable": exc.status >= 500}, "request_id": uuid4().hex}, exc.status)
        elif isinstance(exc, (json.JSONDecodeError, UnicodeDecodeError, ValueError, TypeError)):
            self._send_json({"error": {"code": "INVALID_REQUEST", "message": "请求参数或 JSON 格式无效", "retryable": False}, "request_id": uuid4().hex}, 400)
        else:
            self._send_json({"error": {"code": "PROCESSING_FAILED", "message": "服务端处理失败，请检查输入或重新探测连接", "retryable": True}, "request_id": uuid4().hex}, 503)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/status":
                self._send_json(SERVICE.status(probe=True))
            elif path == "/api/options":
                self._send_json(SERVICE.options())
            elif path.startswith("/api/assets/"):
                asset = SERVICE.asset(path.rsplit("/", 1)[-1])
                content = asset.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", mimetypes.guess_type(asset.name)[0] or "application/octet-stream")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(content)
            elif path.startswith("/api/"):
                raise ServiceError("接口不存在", "NOT_FOUND", 404)
            else:
                candidate = Path(self.translate_path(path)).resolve()
                if not candidate.is_relative_to((ROOT / "frontend").resolve()) or any(part.startswith(".") for part in candidate.relative_to(ROOT / "frontend").parts):
                    raise ServiceError("资源不可访问", "NOT_FOUND", 404)
                super().do_GET()
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as exc:
            self._error(exc)

    def do_POST(self) -> None:
        try:
            origin = self.headers.get("Origin")
            if origin and urlparse(origin).netloc != self.headers.get("Host"):
                raise ServiceError("仅允许同源请求", "FORBIDDEN", 403)
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 1_000_000:
                raise ServiceError("请求体应为 1 MB 以内的 JSON 对象", "INVALID_BODY", 400)
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(body, dict):
                raise ServiceError("请求内容必须是 JSON 对象", "INVALID_BODY", 400)
            routes = {"/api/plan": SERVICE.plan, "/api/generate": SERVICE.generate, "/api/revise": SERVICE.revise, "/api/export": SERVICE.export, "/api/connection/probe": lambda _: SERVICE.status(probe=True)}
            path = urlparse(self.path).path
            if path == "/api/task/validate":
                try:
                    SERVICE._task(body.get("task", body))
                    self._send_json({"valid": True, "field_errors": {}})
                except ServiceError as exc:
                    self._send_json({"valid": False, "field_errors": {"task": str(exc)}})
            elif path in routes:
                self._send_json(routes[path](body))
            else:
                raise ServiceError("接口不存在", "NOT_FOUND", 404)
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as exc:
            self._error(exc)


def main() -> None:
    """Start the localhost-only server; environment supplies an optional port."""
    host = "127.0.0.1"
    port = int(os.getenv("AGENT_PORT", "8765"))
    server = ThreadingHTTPServer((host, port), ApiHandler)
    print(f"华为 PC 营销智能体：http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
