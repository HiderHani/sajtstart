# =============================================================================
# terraform.tfvars – KUNDENS BESTÄLLNINGSLAPP
# =============================================================================
# Här står bara DATA, ingen logik. Det är som ett formulär som fylls i per kund.
# Terraform läser den här filen automatiskt vid "terraform plan" och "apply".
# Vilka rutor som FÅR finnas (och kontrollerna av dem) står i variables.tf.
#
# Ny kund? Byt värdena nedan och kör "terraform apply" igen. Ingen annan kod
# behöver ändras.
#
# Tips: allt efter # är en kommentar. Den är för människor, Terraform hoppar
# över den.
# =============================================================================

# Kundens namn. Hamnar i <title> och som stor rubrik högst upp på varje sida.
client_name = "BilStereo Pro"

# Mappens namn: sajten skapas i sites/bilstereo-pro/.
# Bara små bokstäver, siffror och bindestreck (kontrolleras i variables.tf).
site_slug = "bilstereo-pro"

# Kundens färg som hexkod (röd). Sätts in i CSS:en som variabeln --primary
# och används i sidhuvudet, sloganen och knappen.
primary_color = "#dc2626"

# Sloganen. Syns bara på startsidan (styrs av is_home i main.tf).
tagline = "Bilstereo, högtalare och förstärkare – vi monterar åt dig"

# Sidorna. Det här är en "map": en lista med par.
#   VÄNSTER sida = filnamnet  (produkter -> produkter.html)
#   HÖGER sida   = texten i menyn och sidans rubrik ("Produkter")
#
# for_each i main.tf skapar EN fil per rad: 5 rader = 5 HTML-sidor.
# Lägg till en rad, t.ex.  galleri = "Galleri",  så får sajten en sida till
# och menyn på ALLA sidor uppdateras automatiskt.
#
# Sidan "bestall" får automatiskt ett beställningsformulär (is_order i main.tf).
# Sidan "index" måste finnas – den är startsidan (kontrolleras i variables.tf).
pages = {
  index     = "Hem"
  produkter = "Produkter"
  om-oss    = "Om oss"
  bestall   = "Beställ"
  kontakt   = "Kontakt"
}
