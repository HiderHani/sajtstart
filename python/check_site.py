"""
check_site.py - Kontrollerar att en sajt som Terraform skapat är hel.

1. Hämtar sajtens mapp från Terraform med 'terraform output -json'.
2. Kontrollerar att alla filer Terraform skapat finns.
3. Kontrollerar att varje HTML-sida har en <title>.
4. Hittar trasiga länkar (href/src som pekar på filer som inte finns).
   Bilder som saknas räknas inte som fel - de hamnar i en bildlista.
5. Loggar och sparar en rapport i reports/.
6. Om allt är OK: skickar ett "klart"-meddelande + bildlistan till ORION.

Körs så här (från projektmappen, efter 'terraform apply'):
    python3 python/check_site.py
Utan Terraform (t.ex. för test):
    python3 python/check_site.py --site-dir sites/cafe-solna

Exitkod 0 = sajten är OK, 1 = problem hittades.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
TERRAFORM_DIR = PROJECT_DIR / "terraform"
LOG_FILE = PROJECT_DIR / "logs" / "check_site.log"
REPORT_DIR = PROJECT_DIR / "reports"

# ORIONs inkorg: en mapp som ORION läser. Kan ändras med miljövariabeln ORION_INBOX.
ORION_INBOX = Path(os.environ.get("ORION_INBOX", PROJECT_DIR / "orion_inbox"))

# Mappar och filer som alltid ska finnas i en sajt
REQUIRED = ["index.html", "css/style.css", "js/main.js", "img"]
IMAGE_TYPES = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg")


def setup_logging():
    """Loggar till både skärmen och logs/check_site.log."""
    LOG_FILE.parent.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def get_terraform_output():
    """Kör 'terraform output -json' och returnerar resultatet som dict."""
    try:
        result = subprocess.run(
            ["terraform", "output", "-json"],
            cwd=TERRAFORM_DIR,
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        logging.error("Terraform är inte installerat (hittar inte 'terraform')")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        logging.error(f"terraform output misslyckades: {e.stderr.strip()}")
        sys.exit(1)

    data = json.loads(result.stdout)
    if not data:
        logging.error("Inga outputs från Terraform. Kör 'terraform apply' först.")
        sys.exit(1)

    # terraform output -json ger {"namn": {"value": ...}} – plocka ut värdena
    return {key: item["value"] for key, item in data.items()}


class LinkParser(HTMLParser):
    """Samlar ihop titel och alla länkar (href/src) i en HTML-fil."""

    def __init__(self):
        super().__init__()
        self.links = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        for name, value in attrs:
            if name in ("href", "src") and value:
                self.links.append(value)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data.strip()


def is_local(link):
    """Externa länkar (http, mailto, #) kontrolleras inte."""
    return not link.startswith(("http://", "https://", "mailto:", "tel:", "#"))


def is_image(link):
    return link.lower().endswith(IMAGE_TYPES)


def check_site(site_dir, expected_pages):
    """Gör alla kontroller. Returnerar (problem, bilder som behövs, antal sidor)."""
    problems = []
    images_needed = []

    # 1. Obligatoriska filer och mappar
    for item in REQUIRED:
        if not (site_dir / item).exists():
            problems.append(f"Saknas: {item}")

    # 2. Alla sidor som Terraform skapat ska finnas
    for page in expected_pages:
        if not (site_dir / page).exists():
            problems.append(f"Sidan {page} saknas (finns i Terraform men inte på disk)")

    # 3 och 4. Titel och länkar i varje HTML-fil
    html_files = sorted(site_dir.glob("*.html"))
    for html_file in html_files:
        parser = LinkParser()
        try:
            parser.feed(html_file.read_text(encoding="utf-8"))
        except OSError as e:
            problems.append(f"Kan inte läsa {html_file.name}: {e}")
            continue

        if not parser.title:
            problems.append(f"{html_file.name}: saknar <title>")

        for link in parser.links:
            if not is_local(link) or (site_dir / link).exists():
                continue
            if is_image(link):
                # Bilder som inte finns än är inget fel - de ska skapas (t.ex. av AI)
                images_needed.append({"page": html_file.name, "file": link})
            else:
                problems.append(f"{html_file.name}: trasig länk -> {link}")

    logging.info(f"Kontrollerade {len(html_files)} HTML-sidor")
    if images_needed:
        logging.info(f"{len(images_needed)} bilder behöver skapas")
    return problems, images_needed, len(html_files)


def save_report(report):
    """Sparar rapporten som JSON i reports/."""
    REPORT_DIR.mkdir(exist_ok=True)
    report_file = REPORT_DIR / f"{Path(report['site_dir']).name}.json"
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report_file


def send_to_orion(report):
    """
    Skickar ett 'klart'-meddelande till ORION.
    - Alltid: lägger en JSON-fil i ORIONs inkorg (en mapp som ORION läser).
    - Om ORION_WEBHOOK är satt: skickar också samma JSON med HTTP POST.
    """
    message = {
        "from": "sajtstart",
        "type": "site_ready",
        "text": f"Sajten för {report['client']} är klar med {report['pages_checked']} sidor. "
                f"{len(report['images_needed'])} bilder behöver skapas.",
        **report,
    }

    ORION_INBOX.mkdir(parents=True, exist_ok=True)
    inbox_file = ORION_INBOX / f"{Path(report['site_dir']).name}.json"
    inbox_file.write_text(json.dumps(message, indent=2, ensure_ascii=False), encoding="utf-8")
    logging.info(f"Skickat till ORION (inkorg): {inbox_file}")

    webhook = os.environ.get("ORION_WEBHOOK")
    if not webhook:
        return

    try:
        request = urllib.request.Request(
            webhook,
            data=json.dumps(message).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            logging.info(f"Skickat till ORION (webhook): HTTP {response.status}")
    except (urllib.error.URLError, OSError) as e:
        # ORION offline ska inte stoppa allt - filen i inkorgen finns ändå
        logging.warning(f"Kunde inte nå ORION via webhook: {e}")


def main():
    parser = argparse.ArgumentParser(description="Kontrollera en sajt skapad av Terraform")
    parser.add_argument("--site-dir", help="Hoppa över Terraform och kontrollera denna mapp")
    args = parser.parse_args()

    setup_logging()
    logging.info("Startar kontroll av sajt")

    if args.site_dir:
        site_dir = Path(args.site_dir).resolve()
        client = site_dir.name
        pages = {}
        expected_pages = []
    else:
        tf = get_terraform_output()
        site_dir = Path(tf["site_dir"])
        client = tf["client_name"]
        pages = tf["pages"]
        expected_pages = tf["page_files"]
        logging.info(f"Terraform: {client}, {len(expected_pages)} sidor i {site_dir}")

    if not site_dir.is_dir():
        logging.error(f"Mappen {site_dir} finns inte")
        sys.exit(1)

    problems, images_needed, pages_checked = check_site(site_dir, expected_pages)
    report = {
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "client": client,
        "site_dir": str(site_dir),
        "pages": pages,
        "pages_checked": pages_checked,
        "status": "OK" if not problems else "FAIL",
        "problems": problems,
        "images_needed": images_needed,
    }
    report_file = save_report(report)

    if problems:
        for p in problems:
            logging.error(p)
        logging.error(f"FAIL: {len(problems)} problem hittades. Skickas inte till ORION. Rapport: {report_file}")
        sys.exit(1)

    logging.info(f"OK: sajten för {client} är hel. Rapport: {report_file}")
    send_to_orion(report)
    sys.exit(0)


if __name__ == "__main__":
    main()
