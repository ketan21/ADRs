# ADR-009: No Plaintext Passwords in Logs or Audit

## Status
Accepted

## Context
Passwords are plaintext during rotation (generated in Pega, sent to bridge, stored in AKV). We must ensure they never leak into logs, audit trails, or error messages.

## Decision
- **Pega side**: The plaintext password is stored only in a transient Activity parameter (`Param.NewPassword`). It is **not** written to `pxObjClass`, audit records, or tracer output. The `Connect-REST` message body contains it, but Pega Connect-REST logging must be disabled or redacted for this service.
- **Azure bridge side**: The Function/Logic App **never** logs the `newPassword` field. Application Insights / run history shows `operatorId` and `timestamp` only.
- **AKV side**: Secret contents are encrypted at rest with platform-managed keys. Soft-delete and purge protection are enabled.

## Consequences
- Developers debugging rotation issues will not see passwords in logs.
- If AKV is compromised, soft-delete allows recovery within retention period.
- Additional operational burden: log redaction rules, AKV soft-delete monitoring.

## Rationale
Plaintext passwords in logs are a common and severe security anti-pattern. Explicit prevention at every layer is mandatory.
