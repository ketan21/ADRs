# ADR-004: Password Generation Happens Inside Pega

## Status
Accepted

## Context
Passwords could be generated either inside Pega or by the external Azure bridge.

## Decision
Password generation will happen **inside Pega** using `pxRandomString` in an Activity. The generated plaintext is stored temporarily in a parameter, set on `Data-Admin-Operator-ID.pyPassword`, and committed via `Obj-Save`. Pega automatically hashes `pyPassword` during save.

## Consequences
- Pega controls password complexity, length, and entropy rules.
- The plaintext password exists only transiently in the Activity's parameter page and the HTTP POST body to the Azure bridge.
- No plaintext password is persisted in Pega's database; only the hash is stored.

## Rationale
Using `pyPassword` (not `pyPasswordHash`) ensures Pega's standard hashing pipeline applies. This is the only supported programmatic mechanism for password change in PRPC.
