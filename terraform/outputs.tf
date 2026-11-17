# =============================================================================
# outputs.tf – BRON TILL PYTHON
# =============================================================================
# Outputs är information som Terraform lämnar ut EFTER apply.
# Python (check_site.py) kör "terraform output -json" och får då allt nedan som
# JSON. Så vet Python exakt var sajten ligger och vilka filer som SKA finnas,
# utan att gissa sökvägar.
#
# JSON-formatet ser ut ungefär så här:
#   { "site_dir": { "value": "/Users/.../sites/bilstereo-pro", ... }, ... }
# Python plockar sedan ut "value" ur varje låda.
# =============================================================================

# Hela sökvägen till sajtens mapp.
# abspath gör den absolut (fullständig), så att Python hittar rätt mapp
# oavsett vilken mapp Python körs ifrån.
output "site_dir" {
  description = "Mappen där sajten skapades"
  value       = abspath(local.site_dir)
}

# Kundens namn – hamnar i rapporten och i meddelandet till ORION.
output "client_name" {
  value = var.client_name
}

# Hela sidlistan (filnamn => rubrik) – hamnar i rapporten.
output "pages" {
  description = "Sidornas filnamn och rubriker"
  value       = var.pages
}

# FACIT: alla HTML-filer som Terraform skapade, t.ex. ["index.html", ...].
# [for p in ... : ...] är en for-loop som bygger en lista.
# basename tar bort mappen och lämnar bara filnamnet.
# Python jämför den här listan med det som faktiskt finns på disken.
output "page_files" {
  description = "Alla HTML-filer som skapades"
  value       = [for p in local_file.page : basename(p.filename)]
}
