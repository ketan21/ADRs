# ADR-008: Azure Bridge Component — Azure Function vs Logic App

## Status
Accepted

## Context
The external Azure bridge (ADR-005) can be implemented as either an Azure Function or an Azure Logic App. Both support Managed Identity and HTTP triggers.

## Decision
**Azure Function** (Consumption plan, Python runtime).

Full code control, unit testability, standard CI/CD via GitHub Actions, Application Insights integration, and predictable HTTP trigger behavior. Cold start (1-2s) is acceptable for a daily batch job.

## Consequences
- We write Python code for the bridge, version-controlled in this repo or a dedicated repo.
- Standard CI/CD: `func azure functionapp publish` or container deploy via GitHub Actions.
- Error handling (retry, dead-letter, circuit breaker) is fully custom.
- If serverless cold start becomes an issue, can migrate to Premium plan or containerize later.

## Rationale
Long-term maintainability and testing outweigh the zero-code convenience of Logic Apps. A daily batch job tolerates 1-2s cold start.
