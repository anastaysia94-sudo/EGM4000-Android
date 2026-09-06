# EGM4000 — Public Full-Stack Track

This is the canonical database-backed web/PWA service layered on the Android and local Web/PWA work.

## Implemented
- secure account registration/login with PBKDF2 password hashing, HttpOnly sessions, CSRF and owner authorization
- PostgreSQL in production / SQLite locally
- 237 clearly synthetic seed users, 948 synthetic gameplay sessions and 948 evidence-linked seed tips
- persistent forum threads/replies, blog posts/comments, reports, owner moderation and audit events
- privacy-safe first/returning/registered visitor surveys with consent and pseudonymous identifiers
- dedicated Tips Center with evidence/confidence
- Live Lab normalized `egm.event.v1` events, replay, metrics and learned baselines
- Android bearer-token login/sync endpoints
- owner Admin dashboard and survey builder
- installable responsive PWA for Android/iPhone/iPad/Windows/macOS browsers

## Source packaging
`server.py` deterministically assembles the tested plain UTF-8 fragments under `source_parts/` before running. This avoids connector truncation while keeping every source fragment readable and versioned; no base64 source reconstruction is used.

## Local run
```bash
cd fullstack
export EGM_OWNER_PASSWORD='use-a-new-long-secret'
python server.py
```
Open http://127.0.0.1:8040.

## Production
Set `DATABASE_URL`, `EGM_OWNER_PASSWORD`, `EGM_VISITOR_SECRET`, and `EGM_SECURE_COOKIES=1`. Public production still requires the deployment platform itself to be healthy and monitored.
