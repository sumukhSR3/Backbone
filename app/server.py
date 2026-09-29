"""
Pure Python HTTP Server Adapter.
Provides zero-dependency HTTP server implementation mirroring FastAPI routes.
Runs natively with Python standard library.
"""

import os
import json
import urllib.parse
from typing import Any, Dict, List, Optional, Union
from http.server import HTTPServer, BaseHTTPRequestHandler
from app.database import db
from app.api.ingestion import handle_ingestion
from app.api.fhir import get_fhir_resource, search_fhir_resources
from app.api.review import handle_review
from app.api.metrics import get_metrics
from app.config import HOST, PORT


class ReusableHTTPServer(HTTPServer):
    """
    HTTPServer subclass with SO_REUSEADDR enabled to allow immediate socket reuse.
    """
    allow_reuse_address = True


class APIRequestHandler(BaseHTTPRequestHandler):
    """
    Standard Library HTTP handler routing API endpoints and serving static files.
    """

    def _send_json(self, data: Any, status_code: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, file_path: str, content_type: str):
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404, "File Not Found")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == "/health":
            self._send_json({"status": "ok", "service": "Clinical Data & Principal Diagnosis Review System"}, 200)
            return

        if path == "/" or path == "/index.html":
            template_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
            self._send_file(template_path, "text/html; charset=utf-8")
            return

        if path.startswith("/static/"):
            rel_path = path.replace("/static/", "")
            file_path = os.path.join(os.path.dirname(__file__), "static", rel_path)
            ctype = "text/css" if path.endswith(".css") else "application/javascript" if path.endswith(".js") else "text/plain"
            self._send_file(file_path, ctype)
            return

        if path == "/api/v1/metrics":
            try:
                self._send_json(get_metrics())
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
            return

        # FHIR GET endpoint handling
        if path.startswith("/fhir/"):
            parts = [p for p in path.split("/") if p]
            # /fhir/{resource_type}/{resource_id}
            if len(parts) == 3:
                rtype, rid = parts[1], parts[2]
                res = get_fhir_resource(rtype, rid)
                if res:
                    self._send_json(res, 200)
                else:
                    self._send_json({"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "not-found", "diagnostics": f"{rtype}/{rid} not found"}]}, 404)
                return

            # /fhir/{resource_type}?encounter=...
            elif len(parts) == 2:
                rtype = parts[1]
                enc_id = params.get("encounter", [None])[0]
                pat_id = params.get("patient", [None])[0]
                bundle = search_fhir_resources(rtype, enc_id, pat_id)
                self._send_json(bundle, 200)
                return

        self._send_json({"error": "Not Found", "path": path}, 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length)

        try:
            body_json = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            self._send_json({"error": "Invalid JSON body"}, 400)
            return

        if path == "/api/v1/ingest":
            try:
                res = handle_ingestion(body_json)
                self._send_json(res, 200)
            except ValueError as e:
                self._send_json({"error": str(e)}, 400)
            except Exception as e:
                self._send_json({"error": f"Ingestion error: {str(e)}"}, 500)
            return

        if path == "/api/v1/review/principal-diagnosis":
            try:
                res = handle_review(body_json)
                self._send_json(res, 200)
            except ValueError as e:
                self._send_json({"error": str(e)}, 400)
            except Exception as e:
                self._send_json({"error": f"Review error: {str(e)}"}, 500)
            return

        self._send_json({"error": "Not Found", "path": path}, 404)


def run_server(host: str = HOST, port: int = PORT):
    db.init_db()
    current_port = port
    server = None
    
    # Try binding to configured port, fallback to next available port if in use
    for attempt_port in range(current_port, current_port + 10):
        try:
            server = ReusableHTTPServer((host, attempt_port), APIRequestHandler)
            current_port = attempt_port
            break
        except OSError as e:
            if attempt_port == current_port + 9:
                raise e
            continue

    print(f"🚀 Clinical Data & Principal Diagnosis Review System running at http://{host}:{current_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.server_close()
