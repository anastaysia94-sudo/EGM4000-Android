# EGM4000 AI Continuation Pack

This folder is the handoff pack for continuing EGM4000 with ChatGPT, GitHub Copilot, Grok, Perplexity, or another AI coding/research assistant.

## Repository

Repository: `anastaysia94-sudo/EGM4000-Android`

## Project identity

EGM4000 / EduGameMaster 4000 is a gameplay-intelligence companion for user-authorized fish-shooter style game sessions. It helps a player watch, measure, explain, review, and improve decision quality using evidence from sessions.

Canonical workflow:

`PLAY -> EGM4000 WATCHES -> MEASURES -> ANALYZES -> EXPLAINS -> LEARNS`

## Product boundaries that must not be lost

There are three related but separate products:

1. **EGM4000 / EduGameMaster 4000**
   - Gameplay intelligence, session logging, normalized events, metrics, replay, pattern lab, tips, evidence labels, coaching.
   - May process user-authorized screen/session data.
   - Must not cheat, bypass protections, read hidden state, manipulate balances, promise profit, or predict random outcomes with certainty.

2. **F.S.A. / Fish Shooter Arcade**
   - Separate owned playable fish-shooter arcade app/game.
   - Can provide exact controlled telemetry to EGM4000 as an experimental target.
   - Should remain virtual/non-cash by default.

3. **Founder Console**
   - Owner/admin control plane for settings, users, virtual credits, experiments, content, safety, analytics, and deployment.
   - Must not mutate unauthorized third-party systems or real balances.

Do not merge these into one unsafe app. Shared libraries and shared schemas are allowed.

## Current repository status

This repo now contains:

- `android-egm4000/` — Android app source.
- `web/` — mobile-friendly static web/PWA version.
- `shared/` — normalized gameplay event schema and shared project contracts.
- `docs/` — project notes, safety docs, AI continuation handoff.
- `.github/workflows/build-egm4000-apk.yml` — Android debug APK build workflow.
- `.github/workflows/web-pwa-smoke.yml` — web/PWA smoke-test workflow.

A debug APK was built successfully from GitHub Actions as `EGM4000-Fire-Kirin-Companion-debug-apk` in the Actions artifacts. Treat it as a debug/testing build, not a Play Store release.

## Current Android scope

The Android app is a launchable companion foundation. It should include or preserve these design intentions:

- Fire Kirin companion flow that opens Fire Kirin externally and safely.
- EGM4000 never collects or stores Fire Kirin passwords.
- User-authorized screen feedback using Android screen-capture permission patterns.
- Local session and event logging.
- Evidence labels and confidence values.
- Basic metrics, tips, replay, and session review.
- SV04/SV09 cyber-aquatic premium visual direction.
- Debug APK build through GitHub Actions.

## Current web/PWA scope

The web version should preserve:

- Adult cyber-aquatic dashboard tone.
- Local-first public beta behavior where applicable.
- EGM4000 evidence pipeline language.
- Clear distinction between exact telemetry, observation, estimate, correlation, and hypothesis.
- No promises of guaranteed winnings.
- Mobile/tablet/desktop compatibility.

## Evidence rules

Every assistant continuing this project must label claims and features honestly:

- **Exact telemetry**: produced by owned game/F.S.A. or explicit user-authorized instrumentation.
- **Observed evidence**: visible session behavior captured with user consent.
- **Estimate**: inferred from screen/session signals and should show confidence.
- **Correlation/hypothesis**: not proof and not a prediction.
- **Unknown**: say unknown instead of inventing.

## Brand direction

Adult premium cyberpunk + steampunk + cyber-aquatic control-room. Avoid childish fish-game styling.

Core phrases:

- Parent: `Learn. Build. Play. Grow.`
- Parent: `Build the empire. Control the chaos.`
- EGM4000: `Watch. Measure. Explain. Improve.`
- F.S.A.: `Aim. Shoot. Score. Splash.`
- Founder Console: `Control the chaos.` / `Pressure makes clarity.`

## How to use this pack

Use one of these files depending on the assistant:

- `CHATGPT_CONTINUE_PROMPT.md`
- `COPILOT_CONTINUE_PROMPT.md`
- `GROK_CONTINUE_PROMPT.md`
- `PERPLEXITY_CONTINUE_PROMPT.md`

Use `PROJECT_STATUS_SV09.md` before starting new work.
Use `NEXT_BUILD_PLAN.md` to decide the next concrete milestone.
Use `SAFETY_BOUNDARIES.md` before implementing capture, casino/game, login, balance, or third-party integration features.
