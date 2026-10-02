variable "subscription_id" {
  description = "Azure subscription ID (required by azurerm v4)"
  type        = string
}

variable "prefix" {
  description = "Short name prefix for all resources (lowercase letters/numbers/hyphens)"
  type        = string
  default     = "apimsticky"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus2"
}

variable "instance_count" {
  description = "Number of Document Intelligence instances behind APIM"
  type        = number
  default     = 2
}
