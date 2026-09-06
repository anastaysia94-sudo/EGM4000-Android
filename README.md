# EGM4000 / EduGameMaster 4000

Cyber-aquatic gameplay intelligence for user-authorized session evidence.

**Core loop:** Watch → Measure → Explain → Improve.

This repository contains the current emergency launch rebuild that preserves the established EGM4000 direction while making the project buildable from normal GitHub Actions infrastructure.

## What is included

- `android-egm4000/` — native Android project for EGM4000 Fire Kirin Companion.
- `web/` — local-first EGM4000 web/PWA public beta.
- `shared/` — normalized gameplay event schema plus machine-readable continuity manifest.
- `config/fire-kirin-portal.json` — configured Fire Kirin login portal used by Android and Web/PWA.
- `contracts/` — safe contracts for F.S.A. telemetry and Founder Console integration.
- `docs/` — safety, Fire Kirin companion, release ledger, project status, backlog, and AI continuation documentation.
- `docs/ai-continuation/` — handoff prompts for ChatGPT, GitHub Copilot, Grok, and Perplexity.
- `.github/workflows/build-egm4000-apk.yml` — builds the installable debug APK.
- `.github/workflows/web-pwa-smoke.yml` — checks the web/PWA static build.
- `.github/ISSUE_TEMPLATE/ai-continuation-task.md` — issue template for safe AI continuation tasks.
- `.github/pull_request_template.md` — PR checklist that preserves safety and product boundaries.
- `AGENTS.md` — rules for AI coding agents.

## Continue the project

Before any assistant continues development, read these first:

1. `AGENTS.md`
2. `shared/egm4000.continuity.v1.json`
3. `docs/RELEASE_LEDGER.md`
4. `docs/IMPLEMENTATION_BACKLOG.md`
5. `docs/ai-continuation/README.md`

## AI continuation docs

Use these when continuing the project with another AI assistant:

- `docs/ai-continuation/README.md` — master handoff index.
- `docs/ai-continuation/PROJECT_STATUS_SV09.md` — current status and known unfinished work.
- `docs/ai-continuation/SAFETY_BOUNDARIES.md` — non-negotiable safety rules.
- `docs/ai-continuation/NEXT_BUILD_PLAN.md` — next milestone plan.
- `docs/ai-continuation/UPLOAD_TO_GITHUB_INSTRUCTIONS.md` — GitHub build/upload workflow.
- `docs/ai-continuation/CHATGPT_CONTINUE_PROMPT.md` — prompt for ChatGPT.
- `docs/ai-continuation/COPILOT_CONTINUE_PROMPT.md` — prompt for GitHub Copilot.
- `docs/ai-continuation/GROK_CONTINUE_PROMPT.md` — prompt for Grok.
- `docs/ai-continuation/PERPLEXITY_CONTINUE_PROMPT.md` — prompt for Perplexity.

## Product boundaries

EGM4000, F.S.A., and Founder Console are related but separate products.

- **EGM4000**: analytics, coaching, replay, tips, normalized events, evidence labels.
- **F.S.A. / Fish Shooter Arcade**: separate owned virtual/non-cash fish-shooter game that can provide exact telemetry.
- **Founder Console**: separate owner/admin control plane for settings, safety, telemetry, and experiments.

Do not merge them into one unsafe product.

## Fire Kirin workflow

Configured Fire Kirin login portal:

`https://play.firekirin.xyz/web_game/firekirin777_pc/index.html`

EGM4000 does **not** create a fake Fire Kirin login and does **not** store Fire Kirin credentials.

The safe workflow is:

1. Open EGM4000.
2. Tap **Open Fire Kirin securely**.
3. EGM4000 opens `https://play.firekirin.xyz/web_game/firekirin777_pc/index.html` externally.
4. Sign in directly with Fire Kirin in the browser or official app/site.
5. Return to EGM4000.
6. Start authorized screen feedback.
7. Log session evidence.
8. Review EGM4000 feedback, replay, metrics, and tips.

## Safety boundary

EGM4000 does not guarantee profit, predict random outcomes, infer hidden server state, manipulate balances, bypass protections, or provide live-service cheating. It only explains authorized evidence and clearly labels estimates/hypotheses.

## Build APK

Open GitHub → Actions → **Build EGM4000 Fire Kirin APK**. The output artifact is named:

`EGM4000-Fire-Kirin-Companion-debug-apk`

Inside that artifact is:

`app-debug.apk`

This is a debug/beta APK, not a Play Store production release.

## Web/PWA

Open `web/index.html` locally or host the `web/` folder on HTTPS. Browser screen feedback requires HTTPS and user permission.

## Next build priorities

1. Android Evidence Review v0.2.
2. Web/PWA module hardening.
3. Shared schema validator and fixtures.
4. F.S.A. exact telemetry contract implementation.
5. Founder Console safe control-plane prototype.
6. Signed Android release workflow and device QA.
