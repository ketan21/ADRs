# ADR-002: Direct DB/Blob Update Rejected

## Status
Accepted

## Context
An alternative to using Pega's internal APIs is to directly update the database or blob storage where operator passwords are stored.

## Decision
We will **not** update passwords via direct database or blob manipulation.

## Consequences
- Bypassing Pega's crypto layer (salting, peppering, versioning) would break password hashing and make passwords unreadable by Pega's auth subsystem.
- Audit trail entries (`pxObjClass`, `pxUpdateDateTime`, `pxUpdateOperator`) would be missing, violating compliance requirements.
- Risk of corrupting operator records if schema changes between Pega versions.

## Rationale
Pega's internal auth relies on its own hashing pipeline. Direct DB updates are fragile and unsupported for production use.
