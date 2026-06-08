# ADR-012: Pega External Secret Store (Narrow Scope)

## Status
Accepted

## Context
Pega Infinity 25 introduced External Secret Store (ESS) support, including Azure Key Vault as a backend. This could theoretically eliminate the need for an external bridge.

## Decision
ESS will **not** be used for this use case. The bridge pattern (ADR-005) remains.

## Consequences
- ESS is currently scoped to infrastructure secrets (DB passwords, SMTP credentials, Keystore/Truststore passwords). It does not support arbitrary per-operator secret storage.
- ESS configuration is global per Pega instance, not per operator. The operator-to-secret mapping would be unnatural.
- If Pega expands ESS in a future release to support custom secret types, this ADR should be revisited.

## Rationale
ESS is the wrong abstraction for rotating 10+ individual operator passwords. It is designed for singleton infrastructure credentials, not entity-level secrets.
