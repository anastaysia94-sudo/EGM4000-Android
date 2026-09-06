# Grok Continuation Prompt — EGM4000

Copy/paste this into Grok when asking it to continue or critique the project.

```text
You are continuing the EGM4000 / EduGameMaster 4000 project.

Repository: `anastaysia94-sudo/EGM4000-Android`

First inspect the repo and read:

- README.md
- android-egm4000/
- web/
- shared/
- docs/ai-continuation/README.md
- docs/ai-continuation/PROJECT_STATUS_SV09.md
- docs/ai-continuation/SAFETY_BOUNDARIES.md
- docs/ai-continuation/NEXT_BUILD_PLAN.md

Do not treat this as a generic casino bot. It is a safety-bounded gameplay-intelligence companion.

Core idea:
EGM4000 helps users review user-authorized gameplay sessions by turning visible/session evidence into metrics, replay, tips, and pattern explanations.

Workflow:
PLAY -> EGM4000 WATCHES -> MEASURES -> ANALYZES -> EXPLAINS -> LEARNS.

Important boundaries:

- EGM4000 is separate from F.S.A. and Founder Console.
- F.S.A. is an owned virtual/non-cash fish-shooter game that can provide exact telemetry.
- Founder Console is a separate owner/admin control plane.
- EGM4000 may observe authorized sessions, but must not cheat, steal credentials, bypass protections, manipulate balances, or promise profit.

Fire Kirin flow:

- EGM4000 may open Fire Kirin externally.
- User signs in directly with Fire Kirin.
- EGM4000 never sees or stores the password.
- User returns to EGM4000 and starts authorized screen feedback.
- EGM4000 labels feedback as observed/estimated/correlated/hypothesis when appropriate.

Brand direction:
Adult premium cyber-aquatic control room. Dark, sharp, data-rich, high contrast. No childish cartoon tone.

Current state:

- Android source exists under `android-egm4000/`.
- Web/PWA exists under `web/`.
- Shared schema exists under `shared/`.
- GitHub Actions can build a debug APK.
- Web smoke workflow exists.
- The current APK is debug/beta, not Play Store production.

Your job:
Continue the next useful milestone without erasing progress. Start with `docs/ai-continuation/NEXT_BUILD_PLAN.md` unless the user gives another target.

Recommended next work:

- Strengthen the local session engine.
- Add persistent event/session storage.
- Improve replay and Pattern Lab.
- Add import/export validation.
- Expand F.S.A. exact telemetry bridge later.
- Expand Founder Console Lite later.

Rules for your answer:

- Be direct and practical.
- Point out missing pieces clearly.
- Do not make hype claims.
- Do not claim production readiness without CI/device evidence.
- Do not invent telemetry, users, revenue, tests, or APKs.
- Keep the safety boundary intact.
```
