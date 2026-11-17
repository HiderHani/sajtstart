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
    python3 python/check_site.py --site-dir sites/bilstereo-pro

Exitkod 0 = sajten är OK, 1 = problem hittades.
"""
# Texten ovanför (inom tre citattecken) är en DOCSTRING: en beskrivning av
# hela filen. Den körs inte, den är dokumentation.
#
# KORT OM FILEN: det här är kvalitetskontrollen. Terraform BYGGER sajten,
# check_site.py KONTROLLERAR att den blev hel, och ORION får BESKEDET.
# Ordningen när skriptet körs: main() längst ner startar allt.

# ---------------------------------------------------------------------------
# IMPORTER – allt kommer från Pythons standardbibliotek, inget behöver
# installeras med pip. Färre saker som kan gå fel på redovisningen.
# ---------------------------------------------------------------------------
import argparse  # läser flaggor från kommandoraden, t.ex. --site-dir
import json  # gör om text <-> Python-data (dict/list)
import logging  # skriver loggrader med tid och nivå (INFO, ERROR ...)
import os  # läser miljövariabler (ORION_INBOX, ORION_WEBHOOK)
import subprocess  # kör andra program, här "terraform output -json"
import sys  # sys.exit(...) avslutar programmet med en exitkod
import urllib.error  # felen som kan komma när man skickar över nätet
import urllib.request  # skickar HTTP-anrop (webhooken till ORION)
from datetime import datetime  # tidsstämpel i rapporten
from html.parser import HTMLParser  # läser HTML och hittar taggar
from pathlib import Path  # sökvägar som objekt: mapp / "fil.txt"

# ---------------------------------------------------------------------------
# KONSTANTER – skrivs med STORA BOKSTÄVER enligt Python-konvention.
# ---------------------------------------------------------------------------
# __file__ = den här filen. resolve() gör sökvägen fullständig.
# .parent = mappen python/, .parent.parent = projektmappen sajtstart/.
PROJECT_DIR = Path(__file__).resolve().parent.parent
# Snedstrecket / sätter ihop sökvägar med pathlib: sajtstart/terraform
TERRAFORM_DIR = PROJECT_DIR / "terraform"
LOG_FILE = PROJECT_DIR / "logs" / "check_site.log"
REPORT_DIR = PROJECT_DIR / "reports"

# ORIONs inkorg: en mapp som ORION läser. Kan ändras med miljövariabeln ORION_INBOX.
# os.environ.get("X", standard) = använd miljövariabeln om den finns, annars standard.
ORION_INBOX = Path(os.environ.get("ORION_INBOX", PROJECT_DIR / "orion_inbox"))

# Mappar och filer som alltid ska finnas i en sajt
# (checklistan i steg 1 i check_site nedan).
REQUIRED = ["index.html", "css/style.css", "js/main.js", "img"]
# Filändelser som räknas som bilder. En tuple (parentes) kan användas direkt
# i endswith() för att kolla flera ändelser på en gång.
IMAGE_TYPES = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg")


def setup_logging():
    """Loggar till både skärmen och logs/check_site.log."""
    # Skapa mappen logs/ om den inte finns. exist_ok=True = inget fel om den finns.
    LOG_FILE.parent.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,  # visa INFO och allvarligare (WARNING, ERROR)
        # Hur en rad ser ut: [2026-11-15 21:55:00] [INFO] meddelandet
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        # Två "handlers" = två ställen samtidigt: fil och skärm.
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def get_terraform_output():
    """Kör 'terraform output -json' och returnerar resultatet som dict."""
    # BRON FRÅN TERRAFORM: här läser Python det som står i outputs.tf.
    try:
        result = subprocess.run(
            ["terraform", "output", "-json"],  # kommandot, ett ord per plats
            cwd=TERRAFORM_DIR,  # kör det inne i terraform-mappen
            capture_output=True,  # fånga texten i stället för att skriva ut den
            text=True,  # få texten som str, inte bytes
            check=True,  # felkod från terraform -> CalledProcessError
        )
    # try/except fångar fel så att programmet inte kraschar med en lång felutskrift.
    except FileNotFoundError:
        # Programmet "terraform" finns inte på datorn.
        logging.error("Terraform är inte installerat (hittar inte 'terraform')")
        sys.exit(1)  # exitkod 1 = något gick fel
    except subprocess.CalledProcessError as e:
        # terraform fanns men kommandot misslyckades. e.stderr = felmeddelandet.
        logging.error(f"terraform output misslyckades: {e.stderr.strip()}")
        sys.exit(1)

    # json.loads: gör om JSON-texten till en Python-dictionary.
    data = json.loads(result.stdout)
    # Tom dictionary = inga outputs = ingen har kört "terraform apply" än.
    if not data:
        logging.error("Inga outputs från Terraform. Kör 'terraform apply' först.")
        sys.exit(1)

    # terraform output -json ger {"namn": {"value": ...}} – plocka ut värdena
    # Det här är en DICT COMPREHENSION: en loop som bygger en ny dictionary.
    # Före:  {"site_dir": {"value": "/...", "type": "string"}, ...}
    # Efter: {"site_dir": "/...", ...}   (alla "lådor" öppnade på en gång)
    return {key: item["value"] for key, item in data.items()}


class LinkParser(HTMLParser):
    """Samlar ihop titel och alla länkar (href/src) i en HTML-fil."""

    # LinkParser ÄRVER från HTMLParser (Pythons inbyggda HTML-läsare).
    # HTMLParser läser HTML-koden och anropar våra metoder nedan varje gång
    # den hittar en tagg som öppnas, en tagg som stängs eller text.

    def __init__(self):
        # __init__ körs när man skapar ett objekt: parser = LinkParser()
        super().__init__()  # kör först HTMLParsers egen __init__
        self.links = []  # alla href och src vi hittar
        self.title = ""  # texten i <title>
        self._in_title = False  # "flagga": är vi inne i <title> just nu?

    def handle_starttag(self, tag, attrs):
        # Körs för varje tagg som ÖPPNAS, t.ex. <a href="om-oss.html">.
        # attrs är en lista med par: [("href", "om-oss.html"), ...]
        if tag == "title":
            self._in_title = True
        for name, value in attrs:
            # Spara alla länkar (href) och bilder/skript (src) som inte är tomma.
            if name in ("href", "src") and value:
                self.links.append(value)

    def handle_endtag(self, tag):
        # Körs för varje tagg som STÄNGS, t.ex. </title>. Då sänks flaggan.
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        # Körs för all text mellan taggar. Vi sparar bara texten inne i <title>.
        # strip() tar bort mellanslag och radbrytningar i kanterna.
        if self._in_title:
            self.title += data.strip()


def is_local(link):
    """Externa länkar (http, mailto, #) kontrolleras inte."""
    # startswith med en tuple kollar flera början på en gång.
    # "not" vänder svaret: True = länken pekar på en fil i sajten.
    return not link.startswith(("http://", "https://", "mailto:", "tel:", "#"))


def is_image(link):
    # True om länken slutar med en bildändelse. lower() = gör .JPG till .jpg först.
    return link.lower().endswith(IMAGE_TYPES)


def check_site(site_dir, expected_pages):
    """Gör alla kontroller. Returnerar (problem, bilder som behövs, antal sidor)."""
    # SJÄLVA KONTROLLEN. Två tomma listor som fylls på under kontrollen.
    problems = []  # riktiga fel -> status FAIL
    images_needed = []  # bilder som saknas -> inget fel, skickas till ORION

    # 1. Obligatoriska filer och mappar
    # site_dir / item = sökvägen till filen. exists() = finns den på disken?
    for item in REQUIRED:
        if not (site_dir / item).exists():
            problems.append(f"Saknas: {item}")

    # 2. Alla sidor som Terraform skapat ska finnas
    # expected_pages = FACIT från page_files i outputs.tf.
    for page in expected_pages:
        if not (site_dir / page).exists():
            problems.append(f"Sidan {page} saknas (finns i Terraform men inte på disk)")

    # 3 och 4. Titel och länkar i varje HTML-fil
    # glob("*.html") = alla filer som slutar på .html. sorted = i bokstavsordning.
    html_files = sorted(site_dir.glob("*.html"))
    for html_file in html_files:
        parser = LinkParser()  # en ny parser per fil
        try:
            # Läs filen och mata in texten i parsern.
            parser.feed(html_file.read_text(encoding="utf-8"))
        except OSError as e:
            # Filen gick inte att läsa: notera felet och hoppa till nästa fil.
            problems.append(f"Kan inte läsa {html_file.name}: {e}")
            continue  # continue = hoppa direkt till nästa varv i loopen

        # 3. Tom titel = fel (varje sida ska ha en <title>).
        if not parser.title:
            problems.append(f"{html_file.name}: saknar <title>")

        # 4. Länkarna.
        for link in parser.links:
            # Hoppa över externa länkar och länkar till filer som finns.
            if not is_local(link) or (site_dir / link).exists():
                continue
            if is_image(link):
                # Bilder som inte finns än är inget fel - de ska skapas (t.ex. av AI)
                images_needed.append({"page": html_file.name, "file": link})
            else:
                # Allt annat som saknas är en trasig länk = fel.
                problems.append(f"{html_file.name}: trasig länk -> {link}")

    logging.info(f"Kontrollerade {len(html_files)} HTML-sidor")
    if images_needed:
        logging.info(f"{len(images_needed)} bilder behöver skapas")
    # En funktion kan lämna tillbaka flera värden på en gång (en tuple).
    return problems, images_needed, len(html_files)


def save_report(report):
    """Sparar rapporten som JSON i reports/."""
    REPORT_DIR.mkdir(exist_ok=True)
    # Filen får sajtens mappnamn, t.ex. reports/bilstereo-pro.json
    report_file = REPORT_DIR / f"{Path(report['site_dir']).name}.json"
    # json.dumps = dictionary -> JSON-text.
    # indent=2 = snyggt indragen och lättläst.
    # ensure_ascii=False = å, ä och ö skrivs som de är, inte som å.
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report_file


def send_to_orion(report):
    """
    Skickar ett 'klart'-meddelande till ORION.
    - Alltid: lägger en JSON-fil i ORIONs inkorg (en mapp som ORION läser).
    - Om ORION_WEBHOOK är satt: skickar också samma JSON med HTTP POST.
    """
    # Meddelandet: vem det är från, vilken typ och en text för människor.
    message = {
        "from": "sajtstart",
        "type": "site_ready",
        "text": f"Sajten för {report['client']} är klar med {report['pages_checked']} sidor. "
                f"{len(report['images_needed'])} bilder behöver skapas.",
        # ** packar upp hela rapporten in i meddelandet (alla nycklar följer med).
        **report,
    }

    # Skriv meddelandet som en fil i inkorgen. parents=True skapar även
    # mappar ovanför om de saknas. orion_server.py lämnar sedan ut filen.
    ORION_INBOX.mkdir(parents=True, exist_ok=True)
    inbox_file = ORION_INBOX / f"{Path(report['site_dir']).name}.json"
    inbox_file.write_text(json.dumps(message, indent=2, ensure_ascii=False), encoding="utf-8")
    logging.info(f"Skickat till ORION (inkorg): {inbox_file}")

    # Valfritt extra: en webhook-adress i miljövariabeln ORION_WEBHOOK.
    # Finns ingen adress är vi klara (return = lämna funktionen här).
    webhook = os.environ.get("ORION_WEBHOOK")
    if not webhook:
        return

    try:
        # Bygg ett HTTP POST-anrop med JSON i kroppen.
        request = urllib.request.Request(
            webhook,
            data=json.dumps(message).encode("utf-8"),  # text -> bytes
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        # timeout=5 = vänta högst 5 sekunder, så att skriptet aldrig hänger sig.
        # "with" stänger anslutningen automatiskt efteråt.
        with urllib.request.urlopen(request, timeout=5) as response:
            logging.info(f"Skickat till ORION (webhook): HTTP {response.status}")
    except (urllib.error.URLError, OSError) as e:
        # ORION offline ska inte stoppa allt - filen i inkorgen finns ändå
        # Därför bara en VARNING (warning), inte ett fel.
        logging.warning(f"Kunde inte nå ORION via webhook: {e}")


def main():
    # HÄR STARTAR ALLT.
    # argparse: flaggan --site-dir gör att man kan testa en mapp utan Terraform.
    parser = argparse.ArgumentParser(description="Kontrollera en sajt skapad av Terraform")
    parser.add_argument("--site-dir", help="Hoppa över Terraform och kontrollera denna mapp")
    args = parser.parse_args()

    setup_logging()
    logging.info("Startar kontroll av sajt")

    if args.site_dir:
        # Med flaggan: använd mappen direkt. Inget facit (tom lista).
        site_dir = Path(args.site_dir).resolve()
        client = site_dir.name
        pages = {}
        expected_pages = []
    else:
        # Utan flaggan (det vanliga): fråga Terraform och plocka ut värdena
        # från outputs.tf: mappen, kunden, sidorna och facit.
        tf = get_terraform_output()
        site_dir = Path(tf["site_dir"])
        client = tf["client_name"]
        pages = tf["pages"]
        expected_pages = tf["page_files"]
        logging.info(f"Terraform: {client}, {len(expected_pages)} sidor i {site_dir}")

    # Finns inte mappen alls är det ingen idé att fortsätta.
    if not site_dir.is_dir():
        logging.error(f"Mappen {site_dir} finns inte")
        sys.exit(1)

    # Kör kontrollen. De tre värdena packas upp i tre variabler.
    problems, images_needed, pages_checked = check_site(site_dir, expected_pages)
    # Rapporten är en dictionary som sedan sparas som JSON.
    report = {
        "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "client": client,
        "site_dir": str(site_dir),
        "pages": pages,
        "pages_checked": pages_checked,
        # Villkorsuttryck: "OK" om problemlistan är tom, annars "FAIL".
        "status": "OK" if not problems else "FAIL",
        "problems": problems,
        "images_needed": images_needed,
    }
    report_file = save_report(report)

    # FAIL: logga varje problem som ERROR, skicka INGET till ORION, exitkod 1.
    if problems:
        for p in problems:
            logging.error(p)
        logging.error(f"FAIL: {len(problems)} problem hittades. Skickas inte till ORION. Rapport: {report_file}")
        sys.exit(1)

    # OK: skicka beskedet till ORION och avsluta med exitkod 0.
    logging.info(f"OK: sajten för {client} är hel. Rapport: {report_file}")
    send_to_orion(report)
    sys.exit(0)


# __name__ == "__main__" är bara sant när filen STARTAS direkt
# (python3 python/check_site.py), inte när en annan fil importerar den.
# Då körs main().
if __name__ == "__main__":
    main()
