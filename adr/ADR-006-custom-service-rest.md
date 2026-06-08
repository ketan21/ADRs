# ADR-006: Custom Service REST Rule Required

## Status
Accepted

## Context
Since DX API does not expose password operations (ADR-001), we need a mechanism for the Pega Job Scheduler Activity to either change passwords internally or expose a service for external callers.

## Decision
We will create a **custom `Service REST` rule** named `TestOperator_RotatePassword` (or similar) within a dedicated Service Package. This service will:
- Accept `operatorId` as input
- Run an Activity that generates a new password, updates the operator record, and POSTs the result to the Azure bridge
- Return a success/failure status

## Consequences
- Standard Pega service packaging applies: Service Package with access group, requestor pool, and authentication.
- Can be secured with OAuth 2.0 if called externally, or with internal auth if only the Job Scheduler invokes it.
- The Activity underlying this service is the same one the Job Scheduler calls directly.

## Rationale
The Activity logic is shared between the Job Scheduler (internal trigger) and the Service REST (external/on-demand trigger). Reusing the same Activity ensures consistency.
