"""
orion_server.py - En liten lokal server som visar ORIONs inkorg.

ORION är en HTML-sida (live wallpaper i Plash) och kan inte läsa filer
direkt från disken. Den här servern läser orion_inbox/*.json och
lämnar ut dem på http://localhost:8765/inbox så att ORION kan hämta dem.

Körs så här (i ett eget terminalfönster, från projektmappen):
    python3 python/orion_server.py
Stoppa med Ctrl + C.
"""

import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
INBOX_DIR = PROJECT_DIR / "orion_inbox"
HOST, PORT = "127.0.0.1", 8765   # bara den egna datorn kan ansluta

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")


def read_inbox():
    """Läser alla meddelanden i inkorgen, nyast först."""
    messages = []
    for file in sorted(INBOX_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
        try:
            message = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logging.warning(f"Hoppar över {file.name}: {e}")
            continue
        # id ändras varje gång filen skrivs om -> ORION ser det som ett nytt meddelande
        message["id"] = f"{file.stem}-{int(file.stat().st_mtime)}"
        messages.append(message)
    return messages


class InboxHandler(BaseHTTPRequestHandler):
    def send_json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        # CORS: tillåter ORION-sidan (en lokal fil) att hämta data härifrån
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()

    def do_GET(self):
        if self.path.split("?")[0] == "/inbox":
            self.send_json(200, read_inbox())
        else:
            self.send_json(404, {"error": "Finns bara /inbox"})

    def log_message(self, fmt, *args):
        pass  # tysta varje anrop (ORION frågar var 15:e sekund)


def main():
    INBOX_DIR.mkdir(exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), InboxHandler)
    logging.info(f"ORIONs inkorg körs på http://localhost:{PORT}/inbox ({len(read_inbox())} meddelanden)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Stoppar servern")
        server.server_close()


if __name__ == "__main__":
    main()
