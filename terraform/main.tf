# main.tf - Skapar en ny kundsajt som kod.
#
# Körs så här (i terraform-mappen):
#   terraform init
#   terraform apply
#
# Terraform håller koll på filerna i sitt state. Tas en fil bort
# eller ändras, återskapar 'terraform apply' den.

terraform {
  required_providers {
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

provider "local" {}

locals {
  site_dir = "${var.output_dir}/${var.site_slug}"
}

# En HTML-fil per sida i var.pages (for_each = en resurs per sida)
resource "local_file" "page" {
  for_each = var.pages

  filename = "${local.site_dir}/${each.key}.html"
  content = templatefile("${path.module}/templates/page.html.tftpl", {
    client_name = var.client_name
    tagline     = var.tagline
    title       = each.value
    is_home     = each.key == "index"
    is_order    = each.key == "bestall"
    page_slug   = each.key
    pages       = var.pages
  })
}

# Stilmall med kundens färg
resource "local_file" "css" {
  filename = "${local.site_dir}/css/style.css"
  content = templatefile("${path.module}/templates/style.css.tftpl", {
    primary_color = var.primary_color
  })
}

# Tom JS-fil så att strukturen är på plats
resource "local_file" "js" {
  filename = "${local.site_dir}/js/main.js"
  content  = "// JavaScript för ${var.client_name}\n"
}

# Bildmappen (en .gitkeep gör att mappen skapas)
resource "local_file" "img_placeholder" {
  filename = "${local.site_dir}/img/.gitkeep"
  content  = ""
}
