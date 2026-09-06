# EGM4000 — Runnable Full-Stack Reference

This directory is the database-backed reference track layered on top of the verified Android + Web/PWA v5 work.

## Run locally

```bash
cd fullstack
export EGM_OWNER_PASSWORD='use-a-new-long-random-secret'
python bootstrap_db.py
python server.py
```

Then open `http://127.0.0.1:8040`.

The bootstrap creates **1 owner + 237 fictional test users**, **948 seeded gameplay sessions**, **948 tips**, **Admin 100**, **Monetization 25**, **Return 49**, and the live-event/baseline tables. Fictional test-user passwords are generated fresh into `data/seed_users_credentials.generated.csv`; that file, the SQLite database, owner password, and runtime secrets are gitignored.

## Live intelligence

`Game Session → Capture Adapter → Normalized Gameplay Events → Live Metrics → Pattern/Baseline Learning → Coaching Context → Replay`

- normalized schema: `egm.event.v1`
- evidence labels: exact telemetry, observed evidence, estimate, correlation, hypothesis, unknown
- third-party adapters are read-only/user-authorized evidence sources
- generic motion is an estimate, never hidden-server-state evidence
- F.S.A. remains a separate owned virtual/non-cash product

## Source

- `bootstrap_db.py` — reproducible SQLite seed without committed passwords
- `server.py` — standard-library HTTP/auth/API server
- `live_intelligence.py` — normalized events, metrics, baselines, context packs
- `static/` — mobile-friendly cyber-aquatic reference UI

This is a strong beta/development reference, not a claim that public HTTPS deployment, signed Android release, provider integrations, off-host backups, legal review, or independent penetration testing are complete.
