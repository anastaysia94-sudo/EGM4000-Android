# EGM4000 Feature Registry Summary

Updated: 2026-09-28

The current application registry preserves exactly **100 owner Admin capabilities A001-A100**, exactly **25 monetization capabilities A071-A095**, and **49 return-user features R001-R049**.

## Current Admin 100 truth

`fullstack/admin_registry.py` now classifies **100 implemented / 0 modelled / 0 provider-configuration-required** at the application-capability level. Every A001-A100 entry has a concrete evidence description, and `fullstack/test_admin_registry_complete.py` enforces the 100/0/0 invariant.

This supersedes historical verification snapshots such as `shared/admin100.verified.v6.json`, which correctly recorded the earlier 75 implemented / 25 provider-configuration-required state at that historical revision.

**Important distinction:** a provider-backed capability can be implemented while its live external provider is still unconfigured. The application must fail closed until that provider configuration is supplied and reconciled. Implementation status must not be used to claim a payment, subscription, customer, or revenue event.

## Admin allocation
- A001-A010 — Access & Security
- A011-A020 — Users & Accounts
- A021-A030 — Community Moderation
- A031-A040 — Content & Publishing
- A041-A050 — Surveys & Research
- A051-A060 — Gameplay Intelligence
- A061-A070 — Operations & Analytics
- A071-A095 — Monetization (exactly 25)
- A096-A100 — Governance & Platform

## Return-user registry
The product retains R001-R049 as the canonical return-user feature registry. Adoption must be measured from real usage; implementation does not equal adoption.

## Evidence boundary
Seeded fictional accounts, sessions, tips, posts and survey data are test fixtures. They are never presented as real customers, winnings, commercial traction or third-party evidence.

## Production boundary
Admin-100 source completion does not by itself prove canonical public deployment, production authentication, device distribution, provider configuration, commercial validation, or received revenue. Those remain separate acceptance gates.
