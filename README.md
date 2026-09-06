# EGM4000 / EduGameMaster 4000

Cyber-aquatic gameplay intelligence for user-authorized session evidence.

**Core loop:** Watch → Measure → Explain → Improve.

This repository is the authoritative EGM4000 Android + Web/PWA continuation repository. It preserves EGM4000, Fish Shooter Arcade (F.S.A.), and Founder Console as related but separate products.

## Current consolidated state

- Native Android v0.2 account-aware evidence client with encrypted token storage, incremental sync, personalized Tips, JSON share/import, filters, session summaries, conservative risk flags, and evidence legend.
- Persistent full-stack community/forum/blog backend with registered-user posting, replies/comments, reports, owner moderation, and audit events.
- Privacy-safe first/returning/registered surveys with consent, pseudonymous visitor identifiers, persistent responses, and owner survey builder.
- Responsive installable Web/PWA with Tips Center, Community, Blog, Surveys, Live Lab, account registration/login, and owner Admin controls.
- 237 clearly synthetic seed users, 948 synthetic gameplay sessions, 948 evidence-linked seed tips, and seeded community content for testing.
- Normalized gameplay evidence, live metrics, replay, learned baselines, and F.S.A. exact-telemetry boundary.

## Android v0.2

See `docs/ANDROID_V0_2.md`.

The native client now supports the public-backend contract:

- `POST /api/mobile/login`
- `POST /api/mobile/sync`
- `GET /api/mobile/tips`

The deployed EGM4000 HTTPS server URL is editable in the app and intentionally not hard-coded until the canonical public deployment is finalized.

## Product boundaries

- **EGM4000:** analytics, authorized capture/evidence, coaching, replay, Tips, community, surveys, research, and owner administration.
- **F.S.A. / Fish Shooter Arcade:** separate owned virtual/non-cash fish-shooter game that can provide exact telemetry to EGM4000.
- **Founder Console:** separate owner/admin control plane for owned-product settings and experiments.

## Fire Kirin workflow

EGM4000 opens Fire Kirin externally and never collects or stores Fire Kirin credentials. The user signs in with the provider itself, returns to EGM4000, optionally authorizes screen feedback, records/observes session evidence, and reviews metrics/tips.

## Safety boundary

EGM4000 does not guarantee profit, predict random outcomes, infer hidden third-party server state, manipulate balances, store third-party game passwords, bypass protections, or provide unauthorized live-service cheating. Research features remain limited to local/original/owned/authorized environments and defensive education.

## Build Android APK

GitHub Actions workflow: **Build EGM4000 Android v0.2 APK**.

Artifact: `EGM4000-Android-v0.2-debug-apk` containing `app-debug.apk`.

## Production status

Android v0.2 source is implemented. The public Web/PWA/backend source is deployment-ready. Remaining production gates include the canonical public HTTPS deployment, final Android server URL assignment, signed release/AAB, physical-device QA, monitoring/backups, and production-provider configuration.
