# EGM4000 / EduGameMaster 4000

Cyber-aquatic gameplay intelligence for user-authorized session evidence.

**Core loop:** Watch → Measure → Explain → Improve.

This repository is the authoritative EGM4000 Android + Web/PWA continuation repository. It preserves EGM4000, Fish Shooter Arcade (F.S.A.), and Founder Console as related but separate products.

## Current consolidated state

- Native Android v0.2.1 account-aware evidence client with encrypted token storage, incremental sync, personalized Tips, JSON share/import, filters, session summaries, conservative risk flags, evidence legend, and a canonical HTTPS server-health setup screen.
- Persistent full-stack community/forum/blog backend with registered-user posting, replies/comments, reports, owner moderation, and audit events.
- Privacy-safe first/returning/registered surveys with consent, pseudonymous visitor identifiers, persistent responses, and owner survey builder.
- Responsive installable Web/PWA with Tips Center, Community, Blog, Surveys, Live Lab, account registration/login, and owner Admin controls.
- 237 clearly synthetic seed users, 948 synthetic gameplay sessions, 948 evidence-linked seed tips, and seeded community content for testing.
- Normalized gameplay evidence, live metrics, replay, learned baselines, C006 Tips Center, and the F.S.A. exact-telemetry boundary.

## Android v0.2.1

The native client supports the public-backend contract:

- `GET /api/health`
- `POST /api/mobile/login`
- `POST /api/mobile/sync`
- `GET /api/mobile/tips`

After the first-run tutorial, Android opens a server-connection screen. It validates the configured HTTPS host against `/api/health` and expects `ok=true` plus `schema=egm.event.v1`. The server URL remains editable for staging/recovery. Local evidence logging remains available when the public service is offline.

## Render deployment

The repository root contains `render.yaml`, which defines:

- the `egm4000` public Python web service
- the `egm4000-postgres` PostgreSQL database
- internal `DATABASE_URL` wiring
- generated visitor secret
- secure-cookie mode
- `/api/health` health checking

Deployment runbook: `docs/RENDER_PUBLIC_DEPLOYMENT.md`.

Current external blocker: Render's SmartPickShop workspace is returning HTTP 402 `Payment information is required` when creating both a free Postgres database and a free web service. The application source is deployment-ready; this account-level gate must be cleared before a canonical public URL can exist.

## Product boundaries

- **EGM4000:** analytics, authorized capture/evidence, coaching, replay, Tips, community, surveys, research, and owner administration.
- **F.S.A. / Fish Shooter Arcade:** separate owned virtual/non-cash fish-shooter game that can provide exact telemetry to EGM4000.
- **Founder Console:** separate owner/admin control plane for owned-product settings and experiments.

## Fire Kirin workflow

EGM4000 opens Fire Kirin externally and never collects or stores Fire Kirin credentials. The user signs in with the provider itself, returns to EGM4000, optionally authorizes screen feedback, records/observes session evidence, and reviews metrics/tips.

## Safety boundary

EGM4000 does not guarantee profit, predict random outcomes, infer hidden third-party server state, manipulate balances, store third-party game passwords, bypass protections, or provide unauthorized live-service cheating. Research features remain limited to local/original/owned/authorized environments and defensive education.

## Build Android APK

GitHub Actions workflow: **Build EGM4000 Android v0.2.1 APK**.

Artifact: `EGM4000-Android-v0.2.1-debug-apk` containing `app-debug.apk`.

## Production status

Android v0.2.1 source is implemented and building in CI. The public Web/PWA/backend source is deployment-ready and has a Render Blueprint. Remaining production gates are the Render account billing gate, canonical HTTPS deployment verification, setting that verified public URL as the Android default, signed release/AAB, physical-device QA, monitoring/backups, and production-provider configuration.
