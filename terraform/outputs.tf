# outputs.tf - Information som Python-skriptet läser med
# 'terraform output -json'.

output "site_dir" {
  description = "Mappen där sajten skapades"
  value       = abspath(local.site_dir)
}

output "client_name" {
  value = var.client_name
}

output "pages" {
  description = "Sidornas filnamn och rubriker"
  value       = var.pages
}

output "page_files" {
  description = "Alla HTML-filer som skapades"
  value       = [for p in local_file.page : basename(p.filename)]
}
