# Kund: Frisör Nova
# Körs i en egen workspace så att andra kunders sajter inte påverkas:
#   terraform workspace new frisor-nova
#   terraform apply -var-file=kunder/frisor-nova.tfvars

client_name   = "Frisör Nova"
site_slug     = "frisor-nova"
primary_color = "#7c3aed"
tagline       = "Klippning, färg och styling i centrala Solna"

pages = {
  index    = "Hem"
  tjanster = "Tjänster"
  priser   = "Priser"
  bestall  = "Boka tid"
  kontakt  = "Kontakt"
}
