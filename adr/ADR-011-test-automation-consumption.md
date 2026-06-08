# ADR-011: Test Automation AKV Consumption Pattern

## Status
Accepted

## Context
Downstream test automation (local laptops and Azure DevOps pipelines) needs to retrieve the current password for a given test operator.

## Decision
Test automation will use the Azure Key Vault client library with `DefaultAzureCredential`:
- **Local laptops**: Developer authenticates via `az login` (Azure CLI) or VS Code Azure extension. `DefaultAzureCredential` falls through to `AzureCliCredential`.
- **Azure DevOps pipelines**: Use a Service Connection + `AzureCLI@2` task or a pipeline variable linked to AKV. Alternatively, assign the pipeline's service principal `Get` permission on the Key Vault.

Secret retrieval code (Python example):
```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://<your-vault>.vault.azure.net/", credential=credential)
secret = client.get_secret(f"pega-test-op-{operator_id}")
password = secret.value
```

## Consequences
- No passwords stored in test code, pipeline variables, or environment files.
- Local dev requires Azure CLI login. DevOps pipeline requires Azure service connection setup.
- If AKV is unreachable (e.g., VPN off), tests fail fast with a clear auth error.

## Rationale
Centralizing password storage in AKV means a single rotation updates all consumers atomically. No stale passwords in test configs.
