# EGM4000 Project Status — SV09 Handoff

Last updated: 2026-09-05 Pacific / 2026-09-06 UTC.

## One-line status

EGM4000 is now in a GitHub repository with a direct Android source tree, a web/PWA companion, a shared event schema, documentation, and GitHub Actions workflows. A debug APK build has completed successfully through GitHub Actions.

## Repository

`anastaysia94-sudo/EGM4000-Android`

## What exists now

### Android

Path: `android-egm4000/`

Purpose: Native Android companion app for EGM4000.

Expected capabilities to preserve and expand:

- EGM4000 branded launch screen and core dashboard.
- Fire Kirin companion flow that opens Fire Kirin outside EGM4000.
- Credential-safe design: do not embed a fake Fire Kirin login and do not store Fire Kirin credentials.
- User-authorized screen feedback path.
- Local session/event logger.
- Evidence labels and confidence scores.
- Basic tips/replay/metrics foundation.
- Debug APK workflow.

### Web/PWA

Path: `web/`

Purpose: Mobile-friendly static EGM4000 public-beta web version.

Expected capabilities to preserve and expand:

- Cyber-aquatic dashboard.
- Local-first UI.
- Evidence pipeline messaging.
- Tips, metrics, session review, and safe companion language.
- Installable PWA structure where practical.

### Shared

Path: `shared/`

Purpose: Shared schema and contracts across Android, web, F.S.A., and Founder Console.

Preserve normalized event fields:

- `schemaVersion`
- `sessionId`
- `eventId`
- `timestampMs`
- `source`
- `type`
- `confidence`
- `evidenceClass`
- `gameProfile`
- `payload`

Recommended evidence classes:

- `exact_telemetry`
- `user_entry`
- `screen_observation`
- `screen_estimate`
- `correlation`
- `hypothesis`

### GitHub Actions

Expected workflows:

- `.github/workflows/build-egm4000-apk.yml`
  - Builds an Android debug APK.
  - Uploads an artifact named `EGM4000-Fire-Kirin-Companion-debug-apk`.

- `.github/workflows/web-pwa-smoke.yml`
  - Runs basic static web/PWA checks.

## What was fixed during GitHub setup

An earlier attempt used split base64 files under `buildsrc/`. That failed with `base64: invalid input` before Android compilation began. The correct direction is direct source under `android-egm4000/`, not fragile base64 reconstruction.

## What is not finished yet

Do not claim these are production-complete until implemented and tested:

- Release-signed APK / AAB.
- Play Store ready listing assets.
- Full MediaProjection production pipeline.
- Durable encrypted local database.
- Full replay engine.
- Full pattern lab with statistical validation.
- Full F.S.A. controlled telemetry integration.
- Founder Console backend/admin sync.
- Cloud account sync.
- Public SaaS backend.
- Native Android device QA across Samsung/Pixel/tablet.
- Legal review for any casino-adjacent wording.

## Next best milestone

Priority: turn the debug Android app into a stable beta build with a complete local session model.

Build next:

1. Harden Android project structure.
2. Add persistent Room database or DataStore-backed session storage.
3. Add a real session timeline screen.
4. Add import/export JSON for normalized session bundles.
5. Add sample sessions for replay/testing.
6. Expand the web/PWA with the same shared schema.
7. Add automated tests for event validation and tip generation.
8. Create release signing instructions.

## Non-negotiable safety boundary

EGM4000 is a coaching and analysis companion. It must not become a cheating, credential-harvesting, balance-manipulating, or gambling-profit-prediction tool.
