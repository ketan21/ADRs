# ADR-010: Managed Identity for Azure Bridge Authentication

## Status
Accepted

## Context
The Azure bridge needs to authenticate to Azure Key Vault to call `set_secret`. Options include service principal (client ID + secret), certificate-based auth, or Managed Identity.

## Decision
Use **Azure Managed Identity** (System-assigned) on the Azure Function or Logic App. RBAC assignment: `Key Vault Secrets Officer` (or `Key Vault Administrator` if needed) scoped to the specific Key Vault.

## Consequences
- No credentials (client secrets, certificates) are stored in code, config, or environment variables.
- If the bridge is compromised, the attacker can only interact with the assigned Key Vault, not other Azure resources.
- Managed Identity is not available outside Azure (e.g., local laptop testing). For local dev, use Azure CLI auth (`az login`) with the same Service Principal or use the `AzureCliCredential` fallback.

## Rationale
Managed Identity eliminates credential rotation and secret sprawl. It is the Azure-recommended pattern for app-to-service authentication.
