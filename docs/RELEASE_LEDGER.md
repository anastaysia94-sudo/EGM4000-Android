# EGM4000 Release Ledger

This ledger exists so future AI assistants do not forget what has already been done.

## 2026-09-05 — Emergency launch rebuild

Repository: `anastaysia94-sudo/EGM4000-Android`

### Completed

- Re-established GitHub write access through the connector.
- Confirmed repository existence and public visibility.
- Replaced the brittle split-base64 source reconstruction workflow after it failed with `base64: invalid input`.
- Added direct Android project source under `android-egm4000/`.
- Added safe Fire Kirin companion workflow: open Fire Kirin externally, user signs in directly there, EGM4000 never collects credentials.
- Added Android authorized screen-feedback service foundation.
- Added local session/event logger with evidence labels and confidence values.
- Added basic replay, metrics, and tips foundation.
- Added `web/` local-first PWA public-beta shell.
- Added `shared/` normalized gameplay-event contract area.
- Added project status, safety boundaries, and Fire Kirin companion docs.
- Added GitHub Actions workflow for Android debug APK builds.
- Added GitHub Actions workflow for web/PWA smoke checks.
- Built a debug APK artifact named `EGM4000-Fire-Kirin-Companion-debug-apk`.
- Saved debug APK, artifact ZIP, and checksum to the user's file Library at `/EGM4000/APK/2026-09-05/`.
- Added AI continuation handoff prompts for ChatGPT, GitHub Copilot, Grok, and Perplexity.
- Added root `AGENTS.md` and machine-readable continuity manifest.

### Build classification

- Android: debug/beta APK foundation, not Play Store release.
- Web/PWA: local-first public beta shell, not cloud SaaS.
- F.S.A.: separate product planned; not merged into this app.
- Founder Console: separate product planned; not merged into this app.

### Known unfinished work

- Signed Android release workflow and release keystore handling.
- Real Android device QA on Samsung/Pixel-class devices.
- More robust local persistence model.
- Richer MediaProjection frame analysis, still privacy-preserving and user-authorized.
- Shared JSON schema validator and fixtures.
- Full F.S.A. exact telemetry contract.
- Founder Console admin/control-plane contract.
- Production web deployment over HTTPS.
- Better UI polish across Android and Web/PWA.

## Definition of launch-ready v1.0

EGM4000 v1.0 should be considered launch-ready only when:

1. Android release APK/AAB is signed and install-tested.
2. Web/PWA is deployed over HTTPS and smoke-tested on mobile/tablet/desktop.
3. Event exports from Android and Web/PWA validate against the same schema.
4. Safety copy is present anywhere capture, third-party games, credits, or coaching appear.
5. F.S.A. and Founder Console boundaries are documented and enforced.
6. No user-facing screen promises profit, certainty, hidden-state access, or third-party manipulation.
