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
│   ├── kunder/             # en .tfvars-fil per ny kund (t.ex. frisor-nova.tfvars)
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
- Terraform (`brew install terraform`)
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

### Ny kund utan att röra de andra
Varje kund får en egen Terraform-workspace (eget state) och en egen variabelfil:
```bash
cd terraform
terraform workspace new frisor-nova
terraform apply -var-file=kunder/frisor-nova.tfvars
cd ..
python3 python/check_site.py
```
`terraform workspace list` visar alla kunder, `terraform workspace select default` går tillbaka till BilStereo Pro.
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
- **Workspaces per kund:** en ändring för en kund kan aldrig radera en annan kunds sajt.
- **Bara standardbibliotek i Python** (`subprocess`, `json`, `html.parser`, `logging`):
  inget att installera, färre saker som kan gå fel på redovisningen.

## Resultat
_(Klistra in utdrag från din egen körning här.)_

## Begränsningar
- Kontrollerar bara lokala länkar, inte externa.
- Menyn sorteras i bokstavsordning eftersom Terraform sorterar en `map` efter nyckel.
- `orion_server.py` måste vara igång för att ORION ska få rapporten (filen i `orion_inbox/` skapas ändå).
- Sajten är en grundmall – innehållet skrivs fortfarande för hand.
- Beställningsformuläret skickar inget än (ingen backend).
- Bilderna skapas inte automatiskt ännu – nästa steg är att ORION/AI använder bildlistan.

## Reflektion
_(Skriv själv: vad lärde du dig, vad var svårt, vad skulle du göra annorlunda?)_

## AI och källor
Jag har använt Claude (AI) som stöd för projektidé, kodstruktur och README.
Jag har själv testat lösningen, anpassat kunduppgifterna och gått igenom koden så att
jag kan förklara den. Kursmaterial: Ars1222022/Infrastruktur-konfigurering-och-deployment.
