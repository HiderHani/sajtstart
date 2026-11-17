# Sajtstart – bygger nya kundsajter och lämnar över till ORION

**GitHub:** https://github.com/HiderHani/sajtstart

## Syfte
Jag bygger webbsidor åt kunder. Varje ny sajt börjar med samma manuella steg:
skapa mappar, sidor, meny och CSS med kundens färg. Det tar tid och det är lätt
att glömma något eller få en trasig länk.

Sajtstart automatiserar det:
1. Jag skriver kunden och sidorna (t.ex. Hem + Om oss, Tjänster, Beställ, Kontakt) i `terraform.tfvars`.
2. **Terraform** bygger alla mappar, sidor, meny, CSS och ett beställningsformulär.
3. **Python** kontrollerar att sajten är hel och tar fram en lista över bilder som behövs.
4. Om allt är OK skickar Python ett "klart"-meddelande till **ORION**, min AI-assistent,
   som kan meddela mig och senare ta hand om bilderna med hjälp av AI.

## Tekniker
| Teknik | Roll |
|--------|------|
| **Terraform** (provider `hashicorp/local`) | Infrastructure as Code: beskriver vilka mappar och filer sajten ska ha och skapar dem. Variabler, `for_each`, mallar (`templatefile`), outputs och state. |
| **Python** | `check_site.py` hämtar info från Terraform via `terraform output -json` (subprocess), kontrollerar filer, titlar och länkar, loggar, skriver en rapport och lämnar över till ORION. `orion_server.py` är en liten HTTP-server som lämnar ut ORIONs inkorg. |

Kedja: **Terraform** (skapar) → `terraform output -json` → **Python** (verifierar) → **ORION** (får meddelande + bildlista)

## Struktur
```
sajtstart/
├── README.md
├── terraform/
│   ├── main.tf             # provider + resurser (sidor, css, js, img)
│   ├── variables.tf        # vad som kan ändras per kund (med validering)
│   ├── outputs.tf          # info som Python läser
│   ├── terraform.tfvars    # standardkunden (BilStereo Pro)
│   └── templates/
│       ├── page.html.tftpl # mall för varje sida (meny skapas automatiskt)
│       └── style.css.tftpl # mall för CSS med kundens färg
├── python/
│   ├── check_site.py       # verifiering av sajten + överlämning till ORION
│   └── orion_server.py     # serverar orion_inbox/ på localhost:8765 för ORION
├── sites/                  # här skapar Terraform sajterna
├── logs/                   # check_site.log
├── reports/                # <sajt>.json med resultatet
└── orion_inbox/            # "klart"-meddelanden som ORION läser
```

## Krav
- Terraform (`brew tap hashicorp/tap && brew install hashicorp/tap/terraform`)
- Python 3 (bara standardbiblioteket, inga paket)

## Så kör man projektet
```bash
# 1. Skapa sajten
cd terraform
terraform init      # laddar ner local-providern
terraform plan      # visar vad som kommer skapas
terraform apply     # skapar sajten i ../sites/bilstereo-pro
cd ..

# 2. Kontrollera sajten
python3 python/check_site.py

# 3. Titta på resultatet
open sites/bilstereo-pro/index.html
cat reports/bilstereo-pro.json
cat orion_inbox/bilstereo-pro.json   # det som skickades till ORION

# 4. Låt ORION se rapporterna (i ett eget terminalfönster)
python3 python/orion_server.py
```

## Så testar man
| Test | Förväntat resultat |
|------|--------------------|
| Kör `check_site.py` direkt efter `apply` | `OK`, exitkod 0, meddelande i `orion_inbox/` |
| Öppna `bestall.html` | Beställningsformulär finns (bara på den sidan) |
| Ta bort `sites/bilstereo-pro/om-oss.html` och kör igen | `FAIL` – sidan saknas + trasiga länkar i menyn, exitkod 1, **inget skickas till ORION** |
| Kör `terraform apply` igen | Terraform upptäcker att filen saknas och återskapar den |
| Kör `check_site.py` igen | `OK` igen |
| Sätt `site_slug = "BilStereo Pro"` i tfvars | Terraform stoppar med valideringsfel |
| Lägg till en sida i `pages` och kör `apply` | Ny sida skapas och finns i menyn på alla sidor |

## Felhantering och loggning
- **Terraform:** `validation` på `site_slug` stoppar felaktiga mappnamn innan något skapas.
- **Python:** `try/except` för saknad Terraform, misslyckad `terraform output`, oläsbara filer.
  Tydliga felmeddelanden om man glömt `terraform apply`.
- Allt loggas med tid och nivå till skärm och `logs/check_site.log`.
- Exitkod 0/1 så att andra skript kan se om kontrollen lyckades.
- Saknade bilder räknas inte som fel utan läggs i `images_needed` – de ska skapas senare.
- Om ORION-webhooken inte svarar loggas en varning, men filen i inkorgen finns ändå.

## Tekniska val
- **Terraform i stället för ett vanligt skript:** Terraform beskriver hur sajten *ska* se ut
  (önskat tillstånd) och sparar det i state. Om en fil försvinner eller ändras återställer
  `terraform apply` den. Ett vanligt skript bara kör stegen en gång.
- **`for_each` över `pages`:** en ny sida = en rad i tfvars, menyn uppdateras automatiskt.
- **Python läser `terraform output -json`:** Python behöver inte gissa sökvägar – det får
  exakt vilka filer Terraform skapat. Det är det som kopplar ihop verktygen.
- **Inkorgsmapp + liten server till ORION:** ORION är en webbsida (live wallpaper i Plash) och kan
  inte läsa filer på disken. `orion_server.py` lämnar därför ut inkorgen som JSON på
  `localhost:8765` (bara den egna datorn kan ansluta). ORION frågar var 15:e sekund och ger en rapport.
- **Bara standardbibliotek i Python** (`subprocess`, `json`, `html.parser`, `logging`):
  inget att installera, färre saker som kan gå fel på redovisningen.

## Resultat
Körning på min MacBook (Terraform 1.17.2, Python 3):

```
$ terraform apply
Apply complete! Resources: 8 added, 0 changed, 0 destroyed.

$ python3 python/check_site.py
[INFO] Terraform: BilStereo Pro, 5 sidor i .../sites/bilstereo-pro
[INFO] Kontrollerade 5 HTML-sidor
[INFO] 5 bilder behöver skapas
[INFO] OK: sajten för BilStereo Pro är hel. Rapport: .../reports/bilstereo-pro.json
[INFO] Skickat till ORION (inkorg): .../orion_inbox/bilstereo-pro.json
```

- Sajten för **BilStereo Pro** skapades med 5 sidor (Hem, Produkter, Om oss, Beställ, Kontakt),
  röd färgprofil och ett beställningsformulär på Beställ-sidan.
- ORION visade en rapport om den färdiga sajten inom 15 sekunder.

## Begränsningar
- Kontrollerar bara lokala länkar, inte externa.
- Menyn sorteras i bokstavsordning eftersom Terraform sorterar en `map` efter nyckel.
- `orion_server.py` måste vara igång för att ORION ska få rapporten (filen i `orion_inbox/` skapas ändå).
- Sajten är en grundmall – innehållet skrivs fortfarande för hand.
- Beställningsformuläret skickar inget än (ingen backend).
- Bilderna skapas inte automatiskt ännu – nästa steg är att ORION/AI använder bildlistan.

## Reflektion
Det viktigaste jag lärde mig var hur olika verktyg kan prata med varandra. Terraform skapar sajten
och lämnar ut information med `terraform output -json`, och Python läser den informationen för att
veta exakt vad som ska kontrolleras. När jag förstod det fick jag idén att min AI-assistent ORION
också kunde kopplas in i samma kedja – så att ORION får veta när en sajt är klar och ger mig en rapport.

Det svåraste var att koppla ORION till uppgiften. ORION är en webbsida som körs som bakgrundsbild
och kan inte läsa filer direkt från datorn, så jag löste det med en liten Python-server som lämnar
ut rapporterna. Jag fick också problem med att Terraform inte fanns i Homebrews vanliga lista och
fick installera det från HashiCorps egen källa.

Nästa steg skulle vara att ORION använder bildlistan och tar fram bilderna till sajterna automatiskt.

## AI och källor
Jag har använt Claude (AI) som stöd i projektet:
- för att komma fram till projektidén,
- för att lösa problem på vägen, t.ex. hur jag skulle koppla ORION till uppgiften,
- för att lösa problem i koden och README:n.

Jag har själv valt vad sajterna ska innehålla (t.ex. BilStereo Pro), kört och testat hela
kedjan på min egen dator och gått igenom koden så att jag kan förklara hur den fungerar. Kursmaterial: Ars1222022/Infrastruktur-konfigurering-och-deployment.
