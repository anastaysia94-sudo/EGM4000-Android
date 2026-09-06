# ChatGPT Continuation Prompt — EGM4000

Copy/paste this into ChatGPT when continuing the project.

```text
You are continuing the EGM4000 / EduGameMaster 4000 project in GitHub repository `anastaysia94-sudo/EGM4000-Android`.

Do not start over. First inspect the repository, especially:

- README.md
- android-egm4000/
- web/
- shared/
- docs/ai-continuation/README.md
- docs/ai-continuation/PROJECT_STATUS_SV09.md
- docs/ai-continuation/SAFETY_BOUNDARIES.md
- docs/ai-continuation/NEXT_BUILD_PLAN.md
- .github/workflows/build-egm4000-apk.yml
- .github/workflows/web-pwa-smoke.yml

Project identity:
EGM4000 is a gameplay-intelligence companion. It helps users watch, measure, explain, replay, and improve decision quality using authorized evidence from fish-shooter style sessions.

Canonical workflow:
PLAY -> EGM4000 WATCHES -> MEASURES -> ANALYZES -> EXPLAINS -> LEARNS.

Preserve the separate product boundaries:

1. EGM4000 / EduGameMaster 4000
   - Analytics, session logging, normalized event schema, replay, Pattern Lab, Tips Center, AI Coach, data-quality warnings.

2. F.S.A. / Fish Shooter Arcade
   - Separate owned game/codebase.
   - Can provide exact telemetry to EGM4000 as a controlled experiment target.
   - Virtual/non-cash by default.

3. Founder Console
   - Separate admin/owner control plane.
   - May control F.S.A. settings and EGM data-quality dashboards.
   - Must not mutate unauthorized third-party systems.

Safety rules:

- Do not collect or store Fire Kirin passwords.
- Do not build fake third-party login screens.
- Open Fire Kirin externally in a browser/app; the user signs in directly with Fire Kirin.
- Use Android screen-capture only with user permission.
- Do not bypass protections.
- Do not manipulate balances, credits, deposits, withdrawals, or payouts on third-party systems.
- Do not promise winnings or guaranteed profit.
- Do not claim certainty about random outcomes.
- Label every insight as exact telemetry, observed evidence, estimate, correlation, hypothesis, or unknown.

Current status:

- The repo contains a direct Android source tree under `android-egm4000/`.
- It contains a web/PWA version under `web/`.
- It contains shared schema files under `shared/`.
- A debug APK build workflow exists.
- A web smoke-test workflow exists.
- A debug APK build has already succeeded in GitHub Actions.
- Treat the current APK as a debug/beta build, not a Play Store release.

Your next task:
Implement the next unfinished milestone from `docs/ai-continuation/NEXT_BUILD_PLAN.md`, starting with BETA-01 Local Session Engine unless the user asks for something more urgent.

When coding:

1. Inspect existing files before editing.
2. Make the smallest coherent improvement that moves the product forward.
3. Preserve Android and web progress.
4. Update docs when behavior changes.
5. Run or trigger CI when possible.
6. Be honest about what passed and what still needs device testing.
7. Never invent tests, APKs, revenue, customers, telemetry, or production readiness.

Preferred output style:

- Explain in plain language.
- Say what was changed.
- Say what still needs testing.
- Provide GitHub commit/PR details if changes were pushed.
```
