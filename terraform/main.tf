terraform {
  required_version = ">= 1.5"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
}

resource "azurerm_resource_group" "rg" {
  name     = "${var.prefix}-rg"
  location = var.location
}

# Document Intelligence (kind = FormRecognizer). S0 is required:
# only one free (F0) instance is allowed per subscription.
resource "azurerm_cognitive_account" "di" {
  count               = var.instance_count
  name                = "${var.prefix}-di-${count.index + 1}-${random_string.suffix.result}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  kind                = "FormRecognizer"
  sku_name            = "S0"

  # A custom subdomain gives each instance its own hostname and enables Entra ID auth
  custom_subdomain_name = "${var.prefix}-di-${count.index + 1}-${random_string.suffix.result}"

  identity {
    type = "SystemAssigned"
  }

  tags = {
    purpose = "apim-loadbalancing"
  }
}
