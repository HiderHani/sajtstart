"""
orion_server.py - En liten lokal server som visar ORIONs inkorg.

ORION är en HTML-sida (live wallpaper i Plash) och kan inte läsa filer
direkt från disken. Den här servern läser orion_inbox/*.json och
lämnar ut dem på http://localhost:8765/inbox så att ORION kan hämta dem.

Körs så här (i ett eget terminalfönster, från projektmappen):
    python3 python/orion_server.py
Stoppa med Ctrl + C.
"""
# KORT OM FILEN: servern är en BREVBÄRARE. check_site.py lägger meddelanden
# som JSON-filer i orion_inbox/. En webbsida (ORION) får av säkerhetsskäl inte
# läsa filer på disken, men den FÅR fråga en server. Därför lämnar den här
# servern ut inkorgen på en adress som ORION frågar var 15:e sekund.

import json  # Python-data <-> JSON-text
import logging  # loggrader med tid och nivå
# http.server ingår i Python, så inget extra paket (som Flask) behövs.
# ThreadingHTTPServer kan svara på flera anrop samtidigt.
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path  # sökvägar som objekt

# Projektmappen: den här filen, två steg upp (python/ -> sajtstart/).
PROJECT_DIR = Path(__file__).resolve().parent.parent
INBOX_DIR = PROJECT_DIR / "orion_inbox"
# 127.0.0.1 = "den här datorn" (localhost). Port 8765 = "dörrnumret".
# Två värden tilldelas på en rad: HOST = "127.0.0.1" och PORT = 8765.
HOST, PORT = "127.0.0.1", 8765   # bara den egna datorn kan ansluta

# Samma loggformat som i check_site.py, men bara till skärmen.
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")


def read_inbox():
    """Läser alla meddelanden i inkorgen, nyast först."""
    messages = []
    # glob("*.json") = alla JSON-filer i inkorgen.
    # sorted(..., key=...) sorterar efter något vi väljer:
    #   lambda f: f.stat().st_mtime = en liten funktion utan namn som hämtar
    #   tiden när filen senast ändrades.
    # reverse=True = nyast först.
    for file in sorted(INBOX_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
        try:
            message = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            # Trasig eller oläsbar fil: varna och hoppa över i stället för att krascha.
            logging.warning(f"Hoppar över {file.name}: {e}")
            continue
        # id ändras varje gång filen skrivs om -> ORION ser det som ett nytt meddelande
        # file.stem = filnamnet utan .json, t.ex. "bilstereo-pro".
        # id:t blir då t.ex. "bilstereo-pro-1794868000" (namn + tid i sekunder).
        message["id"] = f"{file.stem}-{int(file.stat().st_mtime)}"
        messages.append(message)
    return messages


class InboxHandler(BaseHTTPRequestHandler):
    # En "handler" bestämmer vad servern svarar. BaseHTTPRequestHandler anropar
    # do_GET när någon gör ett GET-anrop och do_OPTIONS vid ett OPTIONS-anrop.

    def send_json(self, status, data):
        # Hjälpmetod: skickar ett svar med statuskod och JSON-data.
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")  # text -> bytes
        self.send_response(status)  # t.ex. 200 = OK, 404 = finns inte
        self.send_header("Content-Type", "application/json; charset=utf-8")
        # CORS: tillåter ORION-sidan (en lokal fil) att hämta data härifrån
        # CORS är som en "biljett": utan den här headern stoppar webbläsaren
        # ORION från att läsa svaret. * = vilken sida som helst får läsa.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)  # själva datan

    def do_OPTIONS(self):
        # Webbläsaren kan först fråga "får jag fråga?" (en CORS-förfrågan).
        # 204 = ja, men utan innehåll. Svaret säger att GET är tillåtet.
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()

    def do_GET(self):
        # split("?")[0] tar bort eventuella parametrar efter ? i adressen.
        if self.path.split("?")[0] == "/inbox":
            # http://localhost:8765/inbox -> inkorgen med kod 200 (OK).
            self.send_json(200, read_inbox())
        else:
            # Alla andra adresser -> 404 (finns inte).
            self.send_json(404, {"error": "Finns bara /inbox"})

    def log_message(self, fmt, *args):
        # Skriver över den inbyggda loggningen så att den inte gör något.
        pass  # tysta varje anrop (ORION frågar var 15:e sekund)


def main():
    INBOX_DIR.mkdir(exist_ok=True)  # skapa inkorgen om den saknas
    # Skapa servern på adressen (HOST, PORT) med vår handler.
    server = ThreadingHTTPServer((HOST, PORT), InboxHandler)
    logging.info(f"ORIONs inkorg körs på http://localhost:{PORT}/inbox ({len(read_inbox())} meddelanden)")
    try:
        server.serve_forever()  # svara på anrop för evigt ...
    except KeyboardInterrupt:
        # ... tills man trycker Ctrl + C. Då stängs servern snällt.
        logging.info("Stoppar servern")
        server.server_close()


# Kör main() bara när filen startas direkt, inte när den importeras.
if __name__ == "__main__":
    main()
