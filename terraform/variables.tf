# variables.tf - Allt som skiljer en kundsajt från en annan.
# Värdena sätts i terraform.tfvars.

variable "client_name" {
  description = "Kundens namn, visas på sajten"
  type        = string
}

variable "site_slug" {
  description = "Mappnamn för sajten (små bokstäver, inga mellanslag)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.site_slug))
    error_message = "site_slug får bara innehålla a-z, 0-9 och bindestreck."
  }
}

variable "primary_color" {
  description = "Huvudfärg i hex, t.ex. #1e40af"
  type        = string
  default     = "#1e40af"
}

variable "tagline" {
  description = "Kort slogan på startsidan"
  type        = string
  default     = ""
}

variable "pages" {
  description = "Sidor som ska skapas: filnamn => rubrik"
  type        = map(string)
  default = {
    index   = "Hem"
    om-oss  = "Om oss"
    kontakt = "Kontakt"
  }

  validation {
    condition     = contains(keys(var.pages), "index")
    error_message = "pages måste innehålla en startsida med nyckeln index."
  }
}

variable "output_dir" {
  description = "Var sajterna ska skapas (relativt terraform-mappen)"
  type        = string
  default     = "../sites"
}
