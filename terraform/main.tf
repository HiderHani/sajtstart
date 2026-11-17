# =============================================================================
# main.tf – RITNINGEN: vilka filer sajten ska bestå av
# =============================================================================
# Körs så här (i terraform-mappen):
#   terraform init    laddar ner providern (en gång)
#   terraform plan    visar vad som skulle hända, ändrar ingenting
#   terraform apply   skapar filerna på riktigt
#
# Terraform är DEKLARATIVT: vi beskriver VAD som ska finnas, inte HUR det görs.
# Terraform minns allt det skapat i sitt state (terraform.tfstate). Tas en fil
# bort eller ändras för hand märker "terraform apply" det och lägger tillbaka den.
# Ett vanligt skript kör bara stegen en gång och glömmer sedan.
#
# Den här filen skapar 8 resurser:
#   5 HTML-sidor (en per rad i pages) + style.css + main.js + img/.gitkeep
# Därför står det "8 added" när man kör apply.
# =============================================================================

# Vilken provider (tillägg) som behövs.
# hashicorp/local kan skapa filer på den egna datorn.
# "~> 2.5" betyder: version 2.5 eller nyare, men under 3.0.
# Exakt version (2.9.1) låses i .terraform.lock.hcl när man kör init.
terraform {
  required_providers {
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

# Providern behöver inga inställningar (tomma klamrar): ingen inloggning,
# det är ju bara vår egen dator.
provider "local" {}

# locals = hjälpvariabler inne i koden (används som local.<namn>).
# site_dir sätter ihop "../sites" + "/" + "bilstereo-pro".
# Dollartecken + klammer betyder "sätt in värdet här" (interpolering).
locals {
  site_dir = "${var.output_dir}/${var.site_slug}"
}

# -----------------------------------------------------------------------------
# RESURS 1: en HTML-fil per sida
# -----------------------------------------------------------------------------
# resource "local_file" "page" = "skapa en fil", och resursen heter page.
# for_each = var.pages betyder: gör det här en gång PER RAD i pages.
#   each.key   = vänster sida, t.ex. "produkter"  (filnamnet)
#   each.value = höger sida,   t.ex. "Produkter"  (rubriken)
# Fem sidor i tfvars -> fem filer. En ny rad i tfvars -> en ny fil.
resource "local_file" "page" {
  for_each = var.pages

  # Filens sökväg, t.ex. ../sites/bilstereo-pro/produkter.html
  filename = "${local.site_dir}/${each.key}.html"

  # templatefile tar mallen och fyller i "hålen" med värdena nedan,
  # som en lucktext. path.module = mappen som den här filen ligger i.
  content = templatefile("${path.module}/templates/page.html.tftpl", {
    client_name = var.client_name # kundens namn
    tagline     = var.tagline     # sloganen
    title       = each.value      # sidans rubrik, t.ex. "Produkter"

    # == betyder "är det lika med?" och ger true eller false.
    is_home  = each.key == "index"   # true bara på startsidan -> visar sloganen
    is_order = each.key == "bestall" # true bara på beställsidan -> visar formuläret

    page_slug = each.key  # filnamnet, används i bildens namn
    pages     = var.pages # hela listan, så att mallen kan bygga menyn
  })
}

# -----------------------------------------------------------------------------
# RESURS 2: stilmallen med kundens färg
# -----------------------------------------------------------------------------
# Samma trick med templatefile, men här skickas bara färgen in.
resource "local_file" "css" {
  filename = "${local.site_dir}/css/style.css"
  content = templatefile("${path.module}/templates/style.css.tftpl", {
    primary_color = var.primary_color
  })
}

# -----------------------------------------------------------------------------
# RESURS 3: en nästan tom JavaScript-fil
# -----------------------------------------------------------------------------
# Finns så att strukturen (js/main.js) är på plats och sidorna kan länka till den.
# \n = radbrytning i slutet av filen.
resource "local_file" "js" {
  filename = "${local.site_dir}/js/main.js"
  content  = "// JavaScript för ${var.client_name}\n"
}

# -----------------------------------------------------------------------------
# RESURS 4: bildmappen
# -----------------------------------------------------------------------------
# En tom fil som heter .gitkeep. Den finns bara för att mappen img/ ska skapas
# (en helt tom mapp går inte att skapa med local_file). Bilderna läggs dit senare.
resource "local_file" "img_placeholder" {
  filename = "${local.site_dir}/img/.gitkeep"
  content  = ""
}
