# EGM4000 Consolidation Test Report — 2026-09-05

Verified locally against the consolidated full-stack runtime and a fresh private seed database.

- Python server compile — PASS
- bootstrap compile — PASS
- browser application JavaScript syntax — PASS
- home route — HTTP 200
- owner accounts: 1
- fictional regular users: 237
- gameplay sessions/tips: 948 / 948
- admin features / monetization / return features: 100 / 25 / 49
- regular-user login — PASS
- owner login — PASS
- regular user Admin request — HTTP 403 `owner_only` — PASS
- adapter registry: 7 profiles — PASS
- Fire Kirin authorized live session creation — PASS
- normalized `egm.event.v1` persistence — PASS
- observed/manual event label — PASS
- motion sample label `estimate` — PASS
- live metrics — PASS
- Replay Lab timeline — PASS
- unconfigured F.S.A. bridge — expected `bridge_not_configured` — PASS

No test asserts hidden server state, guaranteed profit, third-party balance manipulation, credential interception, or live-service bypass behavior.
