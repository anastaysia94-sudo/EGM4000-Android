# EGM4000 Implementation Backlog

Use this backlog to continue development without restarting or forgetting the web app version.

## P0 — Keep current build green

- Keep `.github/workflows/build-egm4000-apk.yml` passing.
- Keep `.github/workflows/web-pwa-smoke.yml` passing.
- Keep `.github/workflows/fullstack-smoke.yml` passing.
- Do not remove Android, Web/PWA, `fullstack/`, `shared/`, or AI continuation docs.
- Do not reintroduce corrupted split-base64 source as the main build path.

## P1 — Android Evidence Review v0.2 — IMPLEMENTED

Implemented in native Android v0.2:

- event filters: all, shots, credit changes, capture events, breaks, warnings;
- JSON export/share using Android share sheet;
- import/paste JSON with required-field validation and 1000-event cap;
- session summary: start/end, shot count, total events, net credit movement, estimated pace, duration, breaks, warnings;
- evidence label legend;
- conservative risk flags for rising pace + credits down, long session, repeated credit-down entries, and no break logged;
- visible reminder that feedback is descriptive evidence, not prediction;
- EGM4000 mobile account login through `/api/mobile/login`;
- Android Keystore encrypted bearer-token storage;
- incremental cross-device evidence sync through `/api/mobile/sync`;
- personalized evidence/confidence Tips refresh through `/api/mobile/tips`;
- editable HTTPS backend URL until the canonical public deployment URL is finalized;
- offline-first local logging and retry-safe failed sync behavior.

Acceptance status:

- Source implemented and version bumped to `0.2.0-native-sync`.
- GitHub Actions builds the installable debug APK and verifies the v0.2 source contract.
- No third-party game credential collection was added.

## P2 — Web/PWA module hardening

The canonical `fullstack/static/` PWA now provides the persistent public-beta path. Continue visual/interaction parity work without removing the local-first `web/` track.

Remaining hardening:

- final public HTTPS deployment and production URL;
- cross-browser/device QA;
- richer Replay/Pattern visualizations;
- public production monitoring and error reporting.

## P3 — Shared schema validator

Goal: make Android and Web/PWA produce the same kind of session evidence.

Tasks:

- Add `shared/fixtures/sample-fire-kirin-session.json`.
- Add `shared/fixtures/sample-fsa-exact-telemetry-session.json`.
- Add a Node or Python validator script.
- Add a GitHub Actions schema validation workflow.
- Document evidence labels and confidence rules.

Acceptance check:

- CI validates all fixtures.
- Android/Web exports can be pasted into validator with clear pass/fail results.

## P4 — F.S.A. exact telemetry contract

Goal: prepare the separate owned fish-shooter game to become EGM4000's clean experimental target.

Tasks:

- Keep `contracts/fsa-egm4000-telemetry.md` current.
- Complete end-to-end exact telemetry test: shot, target, hit, miss, enemy spawn, boss, credit change, power-up, round start/end.
- Keep all F.S.A. credits virtual/non-cash by default.
- Keep privacy and consent language explicit.

Acceptance check:

- F.S.A. remains separate.
- EGM4000 can ingest F.S.A. telemetry as `exact_telemetry`.

## P5 — Founder Console contract

Goal: prepare admin features without creating unsafe balance or third-party manipulation.

Tasks:

- Keep `contracts/founder-console-egm4000.md` current.
- Limit controls to app settings, user roles, content, tips, experiments, feature flags, safety limits, and virtual/non-cash F.S.A. settings.
- Explicitly prohibit third-party balance mutation, credential collection, bypass tools, or hidden-state access.

## P6 — Production release path

Tasks:

- Complete public HTTPS deployment.
- Add signed release workflow documentation.
- Add `docs/ANDROID_RELEASE_SIGNING.md`.
- Add versioning policy.
- Finalize privacy policy for Android/Web.
- Execute physical QA on Samsung Galaxy, Pixel, tablet, and desktop browsers.

Acceptance check:

- Debug APK remains easy to build.
- Signed release build steps are documented without exposing secrets.
- Android v0.2 can point at the canonical public HTTPS EGM4000 endpoint.
