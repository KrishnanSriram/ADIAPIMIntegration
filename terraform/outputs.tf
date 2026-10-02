output "resource_group" {
  value = azurerm_resource_group.rg.name
}

output "di_endpoints" {
  description = "Use these as backend URLs in APIM (append /documentintelligence)"
  value       = { for a in azurerm_cognitive_account.di : a.name => a.endpoint }
}

output "di_keys" {
  description = "Primary keys, one per instance (terraform output -json di_keys)"
  value       = { for a in azurerm_cognitive_account.di : a.name => a.primary_access_key }
  sensitive   = true
}
