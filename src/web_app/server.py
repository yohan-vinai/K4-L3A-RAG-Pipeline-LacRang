"""Small same-origin HTTP server for the OpenDesign frontend and RAG API."""

from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from .support import load_corpus_catalog, load_evaluation_status, run_generation


Generator = Callable[[str, int], dict]
INDEX_FILE = Path(__file__).resolve().parent / "static" / "index.html"


def _default_generator(query: str, top_k: int) -> dict:
    """Import Task 10 lazily so the UI can start while the pipeline is incomplete."""
    from ..task10_generation import generate_with_citation

    return generate_with_citation(query, top_k)


def _catalog_payload() -> dict:
    sources = load_corpus_catalog()
    return {
        "sources": sources,
        "summary": {
            "total": len(sources),
            "legal": sum(item["doc_type"] == "legal" for item in sources),
            "news": sum(item["doc_type"] == "news" for item in sources),
        },
    }


def make_handler(generator: Generator = _default_generator) -> type[BaseHTTPRequestHandler]:
    class WebHandler(BaseHTTPRequestHandler):
        server_version = "GroundedAdmissions/1.0"

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
            path = urlparse(self.path).path
            if path in {"/", "/index.html"}:
                self._send_bytes(INDEX_FILE.read_bytes(), "text/html; charset=utf-8")
                return
            if path == "/api/health":
                catalog = _catalog_payload()
                self._send_json(
                    {
                        "status": "ok",
                        "service": "grounded-admissions-ui",
                        "corpus_sources": catalog["summary"]["total"],
                    }
                )
                return
            if path == "/api/catalog":
                self._send_json(_catalog_payload())
                return
            if path == "/api/evaluation":
                self._send_json(load_evaluation_status())
                return
            self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
            if urlparse(self.path).path != "/api/chat":
                self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)
                return

            try:
                payload = self._read_json()
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
                self._send_json(
                    {"error": "invalid_json"}, status=HTTPStatus.BAD_REQUEST
                )
                return

            query = payload.get("query")
            top_k = payload.get("top_k", 5)
            if not isinstance(query, str) or not query.strip():
                self._send_json(
                    {"error": "query_required"}, status=HTTPStatus.BAD_REQUEST
                )
                return
            if len(query) > 4000:
                self._send_json(
                    {"error": "query_too_long"}, status=HTTPStatus.BAD_REQUEST
                )
                return
            if not isinstance(top_k, int) or isinstance(top_k, bool) or not 3 <= top_k <= 10:
                self._send_json(
                    {"error": "top_k_must_be_between_3_and_10"},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return

            result = run_generation(query.strip(), top_k, generator)
            self._send_json(result)

        def _read_json(self) -> dict:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as error:
                raise ValueError("invalid content length") from error
            if length <= 0 or length > 64_000:
                raise ValueError("invalid request size")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("JSON body must be an object")
            return payload

        def _send_json(
            self, payload: dict, status: HTTPStatus = HTTPStatus.OK
        ) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send_bytes(body, "application/json; charset=utf-8", status)

        def _send_bytes(
            self,
            body: bytes,
            content_type: str,
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            print(f"{self.address_string()} - {format % args}")

    return WebHandler


def create_server(
    host: str = "127.0.0.1", port: int = 8000, generator: Generator = _default_generator
) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(generator))


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the admissions RAG web app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = create_server(args.host, args.port)
    print(f"Grounded admissions UI: http://{args.host}:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server")
    finally:
        server.server_close()
