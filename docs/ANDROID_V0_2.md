# EGM4000 Native Android v0.2

Version: `0.2.0-native-sync`

Native Android v0.2 turns the earlier Fire Kirin companion into an account-aware EGM4000 evidence client while preserving the safe external-login boundary.

## Implemented

- EGM4000 account sign-in through `/api/mobile/login`.
- Thirty-day mobile bearer token stored encrypted with Android Keystore AES/GCM.
- Editable HTTPS EGM4000 server URL; no hard-coded unpublished production endpoint.
- Incremental evidence upload through `/api/mobile/sync` so already-synced local events are not resent on every sync.
- Personalized Tips refresh through `/api/mobile/tips` with platform, evidence, and confidence displayed.
- Fire Kirin still opens externally; EGM4000 never collects Fire Kirin credentials.
- Authorized screen-feedback permission foundation retained.
- Local session start/end controls.
- Event logging for shots, credit movement, breaks, screen-feedback state, and derived warnings.
- Filters: all events, shots, credit changes, capture events, breaks, warnings.
- Session summary: start, end, duration, event count, shot count, net recorded credit movement, credit-down entries, breaks, estimated shot pace, warning count.
- Conservative risk flags: repeated credit-down entries, 60+ minute sessions, 45+ minutes with no logged break, and rising shot pace while recorded credits are down.
- Risk flags are labeled as hypotheses/derived estimates, not predictions.
- JSON share/export through the Android share sheet.
- JSON import/paste with required event-field validation and a 1000-event cap.
- Evidence legend explaining user-recorded evidence, authorized device signals, and derived warning hypotheses.
- Offline-first behavior: local logging continues without an account or network; failed sync preserves unsent local evidence.

## Server dependency

The client is complete but the server URL is intentionally user-configurable until the canonical public deployment is finalized. Network features require an HTTPS EGM4000 service implementing:

- `POST /api/mobile/login`
- `POST /api/mobile/sync`
- `GET /api/mobile/tips`

The current `fullstack/` backend in this repository implements those endpoints.

## Safety boundary

The app analyzes user-recorded/user-authorized evidence. It does not guarantee profit, predict random outcomes, infer hidden third-party server state, store third-party game passwords, manipulate real balances, bypass protections, or deploy unauthorized cheats.
