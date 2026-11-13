"""Read-only n8n preflight gateway. Never talks to social publishing APIs.

Only live-source adapters could authorize future operations; absent adapters fail closed.
The gateway deliberately does not accept client-supplied 'QA passed' assertions.
"""
import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ALLOWED = {"morning_reconciliation", "nightly_audit"}
EVENTS = Path(os.environ.get("AUDIT_DIR", "/audits"))


class Handler(BaseHTTPRequestHandler):
    def send_json(self, code, body):
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path != "/healthz":
            return self.send_json(404, {"error": "not_found"})
        self.send_json(200, {"service": "social-audit-preflight", "mode": "READ_ONLY_FAIL_CLOSED"})

    def do_POST(self):
        if self.path != "/api/run":
            return self.send_json(404, {"error": "not_found"})
        if int(self.headers.get("Content-Length", "0")) > 4096:
            return self.send_json(413, {"error": "payload_too_large"})
        try:
            req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        except Exception:
            return self.send_json(400, {"error": "bad_json"})
        task = req.get("task")
        if task not in ALLOWED:
            return self.send_json(400, {"error": "bad_task"})
        response = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "task": task, "brand_id": 7076410, "timezone": "Europe/Athens",
            "result": "BLOCKED_MISSING_LIVE_CONNECTORS_AND_EXACT_FINAL_QA",
            "writes_performed": 0, "scheduled": 0, "published": 0,
            "reason": "Metricool/Notion/GitHub live source adapters and signed final-review evidence are not configured in this n8n runtime",
        }
        EVENTS.mkdir(parents=True, exist_ok=True)
        with (EVENTS / "preflight.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(response, ensure_ascii=False) + "\n")
        self.send_json(200, response)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()