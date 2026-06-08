# ADR-005: Azure Bridge Mandatory for AKV Interaction

## Status
Accepted

## Context
Pega Infinity 25 supports External Secret Store (ESS) integrations including Azure Key Vault, but the current ESS scope is narrow — primarily for database passwords, SMTP credentials, and similar infrastructure secrets, not for arbitrary operator password storage.

## Decision
An **external Azure bridge** is mandatory. Pega will POST `{operatorId, newPassword, timestamp}` to this bridge via `Connect-REST`. The bridge will authenticate to Azure Key Vault using Managed Identity and store the secret.

## Consequences
- Pega does not need Azure AD app registration or client secrets.
- The bridge is a single-purpose, stateless component with a very narrow API surface.
- Additional network hop adds ~100-300ms latency per rotation, acceptable for a daily batch job.

## Rationale
Pega cannot directly authenticate to Azure Key Vault with the required permissions (`set_secret`) without holding Azure AD credentials, which violates the principle of least privilege for the Pega runtime.
