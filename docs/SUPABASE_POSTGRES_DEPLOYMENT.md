# EGM4000 + Supabase PostgreSQL Deployment

Supabase can serve as EGM4000's durable PostgreSQL layer without changing the application's evidence, account, community, survey, Tips, Replay, experiment, or Android-sync contracts.

## Architecture

- **Database:** Supabase PostgreSQL via `DATABASE_URL`.
- **Application runtime:** the existing EGM4000 Python service (`fullstack/server.py`) running on a compatible container/Python host.
- **Public UI:** served by that same Python service from `fullstack/static/`.
- **Android:** points to the public HTTPS application URL, not directly to database credentials.

Do **not** put a Supabase database password, service-role secret, owner password, or other privileged secret into Android or frontend JavaScript.

## Why this path

The EGM4000 backend already implements server-side authorization, CSRF checks, login/mobile-token handling, moderation, survey privacy logic, normalized gameplay evidence, Tips, Replay, learning baselines and coaching experiments. Keeping those APIs server-side avoids turning privileged database credentials or owner authorization into client-side logic.

## Required environment

Use `fullstack/.env.example` as the contract. Required production values:

- `DATABASE_URL` — provider-issued Supabase PostgreSQL connection string.
- `EGM_OWNER_PASSWORD` — long random secret supplied only to the server runtime.
- `EGM_VISITOR_SECRET` — long random HMAC secret.
- `EGM_SECURE_COOKIES=1`.
- optional `EGM_OWNER_USERNAME`.
- optional `EGM_FSA_TELEMETRY_TOKEN` only when the separate owned F.S.A. service is actually connected.

The Supabase connection URI should retain the SSL parameters supplied/recommended by Supabase.

## Bootstrap behavior

On first server start, EGM4000 creates its application schema and seeds:

- 1 owner account,
- 237 fictional test/community users,
- 948 synthetic historical gameplay sessions,
- 948 evidence-labeled seeded Tips,
- 237 forum threads + replies,
- 237 blog posts + comments,
- first/returning survey definitions,
- Admin 100 / Monetization 25 / Return 49 registries.

Real user passwords are never generated into the public repository. The 237 synthetic credentials are only written to a local generated CSV when using SQLite; PostgreSQL production bootstrap does not emit that credential file.

## PostgreSQL sequence safety

The deterministic seed uses explicit IDs for repeatable fixtures. PostgreSQL `SERIAL` sequences do not automatically advance when explicit IDs are inserted. EGM4000's storage layer now synchronizes the serial sequence immediately before any application auto-ID insert so the first real registration, forum post, blog post, survey, event or other public insert cannot collide with seeded IDs.

This behavior is verified by `.github/workflows/postgres-smoke.yml` against a real PostgreSQL service.

## Production host options

The repository contains provider-neutral deployment files:

- `Dockerfile`
- `railway.toml`
- `Procfile`
- `render.yaml`

The verified Docker image can therefore use Supabase only for PostgreSQL while the Python application runs on Railway, Render once billing is available, or another compatible container host.

## Verification before calling the service live

1. Start the public application with the Supabase `DATABASE_URL`.
2. Verify `GET /api/health` returns `ok: true` and schema `egm.event.v1` over HTTPS.
3. Register a new non-owner user and verify its ID is above the seed range.
4. Login/logout and verify secure cookies.
5. Verify a regular user cannot access owner-only Admin endpoints.
6. Create a forum thread + reply; confirm after reconnect/redeploy that the records persist.
7. Create a blog post + comment + report; verify owner moderation persists.
8. Verify first/returning/registered survey targeting and consent.
9. Login from Android v0.2.1 and sync evidence.
10. Refresh Android Tips and verify the synchronized session appears on Web/PWA.
11. Verify C014 coaching experiment endpoints on Web + mobile.
12. Configure provider backups/monitoring before broad public access.

## Supabase Auth note

EGM4000 currently has its own server-side account/session/mobile-token system. Supabase Auth is therefore **not required** for the first public deployment. Migrating to Supabase Auth later is possible, but should only be done as an explicit authentication migration with user mapping, owner-role enforcement, session/token compatibility, recovery, audit and Android tests. Do not run two competing identity systems casually.

## Safety boundary

Moving to Supabase does not change the product boundary: EGM4000 analyzes user-authorized evidence and does not guarantee winnings, predict random outcomes with certainty, infer hidden third-party server state as fact, store third-party game passwords, manipulate real balances, bypass protections, or deploy unauthorized live-service cheats.
