# AGENTS.md — EGM4000 Continuation Rules

This repository is worked on by multiple AI assistants and humans. Follow these rules before changing code.

## Product identity

EGM4000 / EduGameMaster 4000 is an evidence-based gameplay-intelligence companion. It helps users review user-authorized session evidence and improve decision quality.

Core loop:

`PLAY -> EGM4000 WATCHES -> MEASURES -> ANALYZES -> EXPLAINS -> LEARNS`

Primary tagline: `Watch. Measure. Explain. Improve.`

## Separate products

Do not collapse these into one app:

1. **EGM4000** — analytics, replay, normalized events, tips, coaching, evidence labels.
2. **F.S.A. / Fish Shooter Arcade** — separate owned virtual/non-cash fish-shooter game and exact-telemetry lab.
3. **Founder Console** — separate owner/admin control plane for users, virtual credits, settings, telemetry, safety, and experiments.

Shared libraries and shared schemas are allowed. Unsafe merging is not.

## Non-negotiable safety boundaries

EGM4000 must not:

- collect or store Fire Kirin credentials;
- create fake third-party login forms;
- bypass protections or access hidden server state;
- manipulate third-party balances, credits, payouts, or gameplay;
- guarantee profit or claim random outcomes can be predicted with certainty;
- provide live-service cheating automation.

EGM4000 may:

- open a third-party site/app externally;
- let the user sign in directly with the provider;
- request user-authorized Android/browser screen feedback;
- store local user-recorded events;
- label evidence as exact telemetry, observed evidence, estimate, correlation, hypothesis, or unknown;
- provide conservative coaching based on user-authorized evidence.

## Repository map

- `android-egm4000/` — native Android launch foundation.
- `web/` — local-first web/PWA public beta.
- `shared/` — normalized event schema and machine-readable continuity records.
- `docs/` — safety, status, AI handoff, launch/readiness docs.
- `.github/workflows/` — APK build and web smoke tests.

## Before implementing a feature

1. Read `docs/ai-continuation/README.md`.
2. Read `shared/egm4000.continuity.v1.json`.
3. Check `docs/IMPLEMENTATION_BACKLOG.md`.
4. Preserve safety wording in user-facing screens.
5. Keep Android and Web/PWA behavior conceptually aligned.
6. Keep F.S.A. and Founder Console separate unless building explicit integration contracts.

## Build checks

Android debug APK:

```bash
cd android-egm4000
gradle :app:assembleDebug --stacktrace
```

Web smoke check:

```bash
python3 -m http.server 4173 --directory web
```

Then inspect `web/index.html`, `web/manifest.webmanifest`, and `web/sw.js`.

## Commit style

Use clear commits such as:

- `Add EGM4000 continuity ledger`
- `Improve Android evidence export`
- `Align web PWA with normalized event schema`
- `Add Founder Console integration contract`

Never claim a feature is production-ready unless it is built, tested, and documented.
