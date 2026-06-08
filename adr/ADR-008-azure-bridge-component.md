# ADR-008: Azure Bridge Component — Azure Function vs Logic App

## Status
Proposed

## Context
The external Azure bridge (ADR-005) can be implemented as either an Azure Function or an Azure Logic App. Both support Managed Identity and HTTP triggers.

## Options

| Dimension | Azure Function | Logic App |
|---|---|---|
| Code control | Full (Python/Node/Go) | Low-code designer + expressions |
| Auth to AKV | System or User-assigned MI | System-assigned MI |
| HTTP endpoint | Function trigger | Request trigger |
| Audit/logging | Application Insights + custom | Built-in run history (30 days) |
| Error handling | Full control (retry, dead-letter) | Built-in retry, limited custom |
| Cost | ~€0.20/million executions | ~€0.025/action |
| Cold start | 1-2s (Consumption) | None |
| DevOps | Standard CI/CD, container deploy | ARM/template export |

## Decision
**Pending user selection.**

## Consequences
- If Azure Function: we write Python code, full testability, standard CI/CD via GitHub Actions.
- If Logic App: visual design, faster to prototype, harder to unit-test, ARM templates for IaC.

## Recommendation
Azure Function for long-term maintainability and testing. Logic App if the goal is zero-code deployment by a Pega admin without dev involvement.
