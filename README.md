# Architecture Decision Records

Project: Pega Test Operator Password Rotation + Azure Key Vault

## Context

Automate rotation of expiring Pega test-operator passwords every 30 days and store current passwords in Azure Key Vault for downstream test automation consumption.

## Environment

- Pega version: Infinity 25
- Authentication: Test operators use Pega internal auth; dev operators use SSO
- Operator count: 10+ test operators
- Automation deployment: Runs on local laptops and Azure DevOps pipelines

## ADR Index

| # | Title | Status |
|---|---|---|
| 001 | Pega DX API Excluded for Password Operations | Accepted |
| 002 | Direct DB/Blob Update Rejected | Accepted |
| 003 | Pega Job Scheduler Chosen Over Azure Function Cron | Accepted |
| 004 | Password Generation Happens Inside Pega | Accepted |
| 005 | Azure Bridge Mandatory for AKV Interaction | Accepted |
| 006 | Custom Service REST Rule Required | Accepted |
| 007 | AKV Secret Naming Convention | Accepted |
| 008 | Azure Bridge Component: Azure Function vs Logic App | Accepted |
| 009 | No Plaintext Passwords in Logs or Audit | Accepted |
| 010 | Managed Identity for Azure Bridge Authentication | Accepted |
| 011 | Test Automation AKV Consumption Pattern | Accepted |
| 012 | Pega External Secret Store (Narrow Scope) | Accepted |

## Implementation

See `implementation/IMPLEMENTATION-PLAN.md` for the phased execution plan (6 phases, 7 days).

| Component | Location | Description |
|---|---|---|
| Azure Function Bridge | `implementation/azure-bridge/` | HTTP-triggered Python function storing passwords in AKV |
| Pega Activity Spec | `implementation/pega/` | `TestOperator_ExpiryCheckAndRotate` step-by-step specification |
| Test Automation Example | `implementation/test-automation/` | Python example consuming AKV secrets |
