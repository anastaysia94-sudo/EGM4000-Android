# EGM4000 Portable Public Deployment

The canonical public service is designed to run unchanged on any provider that can run a Python web service and supply PostgreSQL.

## Required runtime contract

- Build from repository root.
- Start command: `python server.py` from `fullstack/`, or use the root `Dockerfile` / `Procfile`.
- HTTP health check: `/api/health`.
- Runtime must expose a public HTTPS URL.
- PostgreSQL is supplied through `DATABASE_URL`.
- The application binds to `0.0.0.0` and the platform-provided `PORT`.

## Required secrets / environment variables

- `DATABASE_URL` — PostgreSQL connection URL supplied by the host/database provider.
- `EGM_OWNER_PASSWORD` — strong owner password supplied as a secret; never commit it.
- `EGM_OWNER_USERNAME` — optional; defaults to `EGM4000Owner`.
- `EGM_VISITOR_SECRET` — long random secret used for privacy-preserving visitor/network HMACs.
- `EGM_SECURE_COOKIES=1` — required for public HTTPS deployment.
- `EGM_FSA_TELEMETRY_TOKEN` — optional; only configure when the separate owned F.S.A. product is actively connected.

## Provider files already in this repository

- `render.yaml` — Render Blueprint for web service + Postgres.
- `railway.toml` — Railway Docker deployment configuration.
- `Dockerfile` — provider-neutral container build.
- `Procfile` — generic Python host start command.

## Render status

The SmartPickShop Render workspace was checked on 2026-09-06. No existing Postgres or web service was available. Attempts to create both resources returned HTTP 402 because Render currently requires payment information on the workspace. This is an account-level infrastructure gate, not an application build failure.

## GitHub Pages status

A GitHub Pages workflow exists for the local-first `web/` PWA. The connected GitHub App successfully validated the PWA but could not create/enable the repository Pages site (`Resource not accessible by integration`). The workflow is now manual-only to avoid red CI until Pages is enabled by an account context with repository Pages administration permission.

GitHub Pages is only a static fallback. It does **not** replace the PostgreSQL-backed shared service required for real registered accounts, cross-device community, shared surveys, Tips synchronization, or Android sync.

## Railway / compatible container host

The root Docker image installs `fullstack/requirements.txt`, copies the canonical full-stack source, and launches `python server.py`. Railway or any similar container host should attach PostgreSQL, inject the required secrets, and probe `/api/health`.

## Supabase option

Supabase can provide PostgreSQL and serverless infrastructure, but the current canonical EGM4000 server is Python. The lowest-risk Supabase use is as the persistent Postgres provider paired with a compatible Python/container host. A full Supabase Edge Function port would be a separate runtime implementation and must preserve all API, authorization, evidence, and privacy contracts before replacing the Python service.

## Production verification sequence

1. `/api/health` returns success over HTTPS.
2. Register a real non-owner account.
3. Sign in/out in Web/PWA.
4. Verify owner-only Admin routes reject the normal account.
5. Create forum thread + reply and verify persistence after a new browser session.
6. Create blog content + comment and test moderation/report flow.
7. Test first/returning/registered survey targeting and consent.
8. Sign in from Android v0.2.1.
9. Sync new evidence from Android.
10. Refresh Tips and confirm the synced session/tips are visible on Web/PWA.
11. Verify backups/monitoring before inviting public users.

## Product safety boundary

Public deployment does not change the EGM4000 evidence rules. It must not guarantee profit, claim certainty about random outcomes, infer hidden third-party server state as fact, store third-party game passwords, manipulate balances, bypass protections, or enable unauthorized live-service cheating.
