# EGM4000 Implementation Backlog

Use this backlog to continue development without restarting or forgetting the web app version.

## P0 — Keep current build green

- Keep `.github/workflows/build-egm4000-apk.yml` passing.
- Keep `.github/workflows/web-pwa-smoke.yml` passing.
- Do not remove Android, Web/PWA, `shared/`, or AI continuation docs.
- Do not reintroduce corrupted split-base64 source as the main build path.

## P1 — Android Evidence Review v0.2

Goal: make the Android app feel like a usable EGM4000 companion rather than only a proof-of-build.

Tasks:

- Add event filters: all, shots, credit changes, capture events, breaks, warnings.
- Add export/share JSON button using Android share sheet.
- Add import/paste JSON screen.
- Add session summary fields: start time, end time, shot count, total events, net credit movement, estimated pace.
- Add evidence label legend inside the app.
- Add conservative risk flags:
  - pace up + credits down;
  - long session duration;
  - repeated credit-down entries;
  - no break logged.
- Add visible reminder: feedback is not a prediction.

Acceptance check:

- App builds with GitHub Actions.
- User can export a session JSON file or share text.
- No credential collection is added.

## P2 — Web/PWA module hardening

Goal: keep the web app alive as a first-class version, not a forgotten demo.

Tasks:

- Split `web/index.html` into clearer module sections or lightweight files.
- Add Command Center, Event Stream, Metrics, Tips, Replay, Data Exchange, Safety, and Settings sections.
- Validate imports before saving.
- Add sample/demo session loader.
- Add PWA install guidance.
- Add no-backend privacy explainer.

Acceptance check:

- Web smoke workflow passes.
- App opens locally with no external dependencies.
- Exported event data follows `shared/normalized-gameplay-event.schema.json`.

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

- Create `contracts/fsa-egm4000-telemetry.md`.
- Define exact telemetry events: shot, target, hit, miss, enemy spawn, boss, credit change, power-up, round start/end.
- Mark all F.S.A. credits as virtual/non-cash by default.
- Add privacy and consent language.
- Add sample telemetry JSON.

Acceptance check:

- F.S.A. remains separate.
- EGM4000 can ingest F.S.A. telemetry as `exact_telemetry`.

## P5 — Founder Console contract

Goal: prepare admin features without creating unsafe balance or third-party manipulation.

Tasks:

- Create `contracts/founder-console-egm4000.md`.
- Define admin-safe controls: app settings, user roles, content, tips, experiments, feature flags, safety limits, virtual/non-cash F.S.A. settings.
- Explicitly prohibit third-party balance mutation, credential collection, bypass tools, or hidden-state access.

Acceptance check:

- Founder Console remains separate.
- Admin controls are scoped to owned products and safe local settings.

## P6 — Production release path

Tasks:

- Add signed release workflow documentation.
- Add `docs/ANDROID_RELEASE_SIGNING.md`.
- Add versioning policy.
- Add privacy policy draft for Android/Web.
- Add testing checklist for Samsung Galaxy, Pixel, tablet, and desktop browser.

Acceptance check:

- Debug APK remains easy to build.
- Release build steps are documented without exposing secrets.
