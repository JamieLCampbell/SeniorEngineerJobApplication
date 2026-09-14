"""Authenticated Cloud Run collector. Semantic validation belongs to Dataflow."""
import base64
import google.auth
from google.auth.transport.requests import AuthorizedSession
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

credentials, _ = google.auth.default()
session = AuthorizedSession(credentials)
topic = "projects/" + os.environ["PROJECT_ID"] + "/topics/assessment-demo-events"

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if self.path != "/events" or not 0 < length <= 16384:
                self.send_error(400); return
            payload = self.rfile.read(length)
            if not isinstance(json.loads(payload), dict):
                self.send_error(400); return
            response = session.post("https://pubsub.googleapis.com/v1/" + topic + ":publish",
                                    json={"messages": [{"data": base64.b64encode(payload).decode()}]}, timeout=30)
            response.raise_for_status()
            message_id = response.json()["messageIds"][0]
        except (ValueError, json.JSONDecodeError):
            self.send_error(400); return
        except Exception:
            self.send_error(503); return
        self.send_response(202)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"message_id": message_id}).encode())

if __name__ == "__main__":
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8080"))), Handler).serve_forever()
