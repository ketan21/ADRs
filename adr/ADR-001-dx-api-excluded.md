# ADR-001: Pega DX API Excluded for Password Operations

## Status
Accepted

## Context
Pega Infinity 25 provides a DX API with 135+ endpoints. We initially considered using the DX API for all operator management operations, including password reset.

## Decision
The DX API does **not** expose any endpoint for password management on `Data-Admin-Operator-ID`. We will **not** use the DX API for password operations.

## Consequences
- A custom `Service REST` rule is required within Pega to handle password changes programmatically.
- The frontend/DX API layer cannot drive this automation; it must be server-side (Activity + Job Scheduler).

## Evidence
- Search of all 135 DX API endpoints in `references/api-endpoints.md` confirmed zero password-management endpoints.
- Pega community documentation confirms `Data-Admin-Operator-ID` password fields are internal and not exposed via REST.
