# terraform.tfvars - Uppgifter om kunden. Byt ut för en ny kund.

client_name   = "BilStereo Pro"
site_slug     = "bilstereo-pro"
primary_color = "#dc2626"
tagline       = "Bilstereo, högtalare och förstärkare – vi monterar åt dig"

# Hem + 4 sidor. Vänster = filnamn, höger = rubrik i menyn.
# Sidan "bestall" får automatiskt ett beställningsformulär.
pages = {
  index     = "Hem"
  produkter = "Produkter"
  om-oss    = "Om oss"
  bestall   = "Beställ"
  kontakt   = "Kontakt"
}