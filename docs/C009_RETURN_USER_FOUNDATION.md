# C009 — Return-user foundation checkpoint

Date: 2026-09-13

This checkpoint replaces the placeholder R001–R049 rows with the canonical 49 feature names and an evidence-based implementation ledger.

## Implemented in this checkpoint

- Authenticated return dashboard API and responsive Today UI.
- Daily insight based on saved session evidence.
- Seven-day story and prior-week activity comparison.
- Healthy evidence-tracking streak that explicitly avoids gambling-reward language.
- Evidence-linked notification feed.
- Contextual feature discovery.
- Rolling 30-day personal evidence report.
- CSRF-protected first-party feature-usage events.
- Owner-only per-feature event, unique-user, and last-used reporting.
- Synthetic seed users are excluded from the eligible real-user denominator.
- Canonical R001–R049 names and honest statuses: 30 implemented, 19 modelled.

## Deliberately not claimed

C009 is not complete. R006, R009, R012–R016, R018, R023–R028, R031–R035 and R041 remain modelled until their end-user behavior and tests exist. No adoption percentage is seeded, fabricated, or guaranteed.

## Verification

- `python test_return_features.py`
- Authenticated API smoke for `/api/return/dashboard`
- CSRF-protected POST smoke for `/api/return/event`
- Owner-only API smoke for `/api/admin/return-adoption`
- Existing C006/C014 integration regression test

