# GitHub Copilot Continuation Prompt — EGM4000

Use this with GitHub Copilot Chat inside the repository.

```text
You are GitHub Copilot working inside repository `anastaysia94-sudo/EGM4000-Android`.

Before writing code, read:

- README.md
- docs/ai-continuation/README.md
- docs/ai-continuation/PROJECT_STATUS_SV09.md
- docs/ai-continuation/SAFETY_BOUNDARIES.md
- docs/ai-continuation/NEXT_BUILD_PLAN.md
- shared/normalized-gameplay-event.schema.json, if present
- .github/workflows/build-egm4000-apk.yml
- .github/workflows/web-pwa-smoke.yml

Do not delete or overwrite the web/PWA progress. Do not remove Android build workflow support. Do not reintroduce the old broken base64/buildsrc reconstruction path unless explicitly asked; the correct direction is direct source under `android-egm4000/`.

Project summary:
EGM4000 is a safe gameplay-intelligence companion for user-authorized fish-shooter style sessions. It logs and explains visible/user-provided/owned telemetry evidence. It does not cheat, collect credentials, bypass protections, or guarantee gambling results.

Important product separation:

- EGM4000 = analytics/coaching/replay/tips/event pipeline.
- F.S.A. = separate owned virtual fish-shooter game that can emit exact telemetry.
- Founder Console = separate owner/admin controls and data-quality dashboards.

Safety constraints to enforce in code:

- Never create a fake Fire Kirin login screen.
- Never request, store, log, or transmit third-party credentials.
- Open Fire Kirin externally.
- Use Android MediaProjection/screen capture only after system user consent.
- Keep third-party sessions observation-only.
- Never manipulate third-party balances, payouts, deposits, withdrawals, credits, or game actions.
- No guaranteed winning language.
- Random outcomes must never be presented as predictable certainties.

Recommended next implementation:
BETA-01 Local Session Engine.

Implement or improve:

1. Kotlin data models for Session and GameplayEvent.
2. Local persistence using Room or DataStore.
3. Session timeline UI in Jetpack Compose.
4. Tips engine that only uses actual logged evidence.
5. Import/export normalized session JSON.
6. Test fixtures for Fire Kirin observation-only, F.S.A. exact telemetry, and manual-entry sessions.
7. Unit tests for event validation and tip generation.

Coding requirements:

- Keep Compose UI readable and mobile-first.
- Prefer small, testable Kotlin files.
- Keep package names stable.
- Add comments where behavior relates to safety, evidence, or uncertainty.
- Update README/docs after feature changes.
- Ensure `.github/workflows/build-egm4000-apk.yml` still builds.

When done, report:

- Files changed.
- Tests run.
- Whether APK workflow should pass.
- Known limitations.
```
