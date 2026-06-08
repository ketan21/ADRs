# ADR-007: AKV Secret Naming Convention

## Status
Accepted

## Context
Azure Key Vault requires a consistent naming scheme for secrets so that test automation can retrieve them predictably.

## Decision
Secret names: `pega-test-op-<operatorId>`

Tags:
- `operator-id`: the Pega operator ID
- `environment`: e.g. `dev`, `test`, `staging`
- `last-rotated`: ISO 8601 timestamp
- `expires`: ISO 8601 timestamp (rotation due date)

## Consequences
- Test automation uses `operatorId` to compute the secret name: `f"pega-test-op-{operator_id}"`
- Tags enable filtering and audit queries in Azure Portal / CLI.
- Secret value contains **only** the plaintext password — no JSON wrapper, no metadata.

## Rationale
Flat naming keeps retrieval logic simple. Tags carry metadata without polluting the secret value.
