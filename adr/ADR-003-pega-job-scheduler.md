# ADR-003: Pega Job Scheduler Chosen Over Azure Function Cron

## Status
Accepted

## Context
Two options for driving the rotation schedule:
- **Option A**: Azure Function cron trigger that calls Pega API
- **Option B**: Pega Job Scheduler that runs an Activity periodically

## Decision
Use **Pega Job Scheduler** (Option B). The scheduler will trigger daily at 06:00 and run an Activity that checks for expiring operators, generates new passwords, and calls the Azure bridge.

## Consequences
- Pega remains the source of truth for operator lifecycle and password policy.
- The external Azure bridge has a simpler contract: receive a password and store it. No scheduling logic needed.
- If Pega is down, rotation does not run — but that's acceptable since test operators can't log in anyway.

## Rationale
User preference: "Pega Job Scheduler" was explicitly chosen over Azure Function cron due to architectural alignment with Pega as the system of record.
