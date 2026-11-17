# =============================================================================
# variables.tf – VILKA UPPGIFTER EN KUND HAR (formuläret)
# =============================================================================
# Här DEKLARERAS varje variabel: vad den heter, vilken typ den har och om den
# har ett standardvärde. Själva värdena fylls i i terraform.tfvars.
#
#   variables.tf     = formuläret (vilka rutor som finns + regler)
#   terraform.tfvars = det ifyllda formuläret (BilStereo Pro)
#
# I koden används en variabel som var.<namn>, t.ex. var.client_name.
#
# validation-blocken är "vakter": Terraform vägrar köra om ett värde är fel,
# INNAN något skapas. Då får man ett tydligt felmeddelande i stället för en
# trasig sajt.
# =============================================================================

# Kundens namn. type = string betyder text.
# Inget default -> värdet MÅSTE fyllas i, annars stoppar Terraform.
variable "client_name" {
  description = "Kundens namn, visas på sajten"
  type        = string
}

# Mappnamnet för sajten (blir sites/<site_slug>/).
variable "site_slug" {
  description = "Mappnamn för sajten (små bokstäver, inga mellanslag)"
  type        = string

  # VAKT 1: regex ^[a-z0-9-]+$ betyder "bara a–z, 0–9 och bindestreck,
  # minst ett tecken, från början (^) till slut ($)".
  # can(...) gör om ett fel till false i stället för att krascha.
  # Exempel: "BilStereo Pro" stoppas (stora bokstäver + mellanslag).
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.site_slug))
    error_message = "site_slug får bara innehålla a-z, 0-9 och bindestreck."
  }
}

# Huvudfärgen. Har ett default (blå), så glömmer man färgen blir sajten blå.
variable "primary_color" {
  description = "Huvudfärg i hex, t.ex. #1e40af"
  type        = string
  default     = "#1e40af"
}

# Sloganen. Default är tom text: ingen slogan, inga problem.
variable "tagline" {
  description = "Kort slogan på startsidan"
  type        = string
  default     = ""
}

# Sidorna. map(string) = par av text: filnamn => rubrik i menyn.
# Defaulten ger tre sidor om tfvars inte säger något annat.
variable "pages" {
  description = "Sidor som ska skapas: filnamn => rubrik"
  type        = map(string)
  default = {
    index   = "Hem"
    om-oss  = "Om oss"
    kontakt = "Kontakt"
  }

  # VAKT 2: keys(var.pages) är alla vänstersidor (filnamnen).
  # contains(...) kollar att "index" finns med. Ingen startsida = ingen sajt.
  validation {
    condition     = contains(keys(var.pages), "index")
    error_message = "pages måste innehålla en startsida med nyckeln index."
  }
}

# Var sajterna hamnar. "../sites" = mappen sites, ett steg UPP från
# terraform-mappen (alltså sajtstart/sites/).
variable "output_dir" {
  description = "Var sajterna ska skapas (relativt terraform-mappen)"
  type        = string
  default     = "../sites"
}
