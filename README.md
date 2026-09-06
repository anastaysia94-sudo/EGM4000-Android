# EGM4000 / EduGameMaster 4000

Cyber-aquatic gameplay intelligence for user-authorized session evidence.

**Core loop:** Watch → Measure → Explain → Improve.

This repository is the authoritative EGM4000 Android + Web/PWA continuation repository. It preserves the established product direction while keeping EGM4000, Fish Shooter Arcade (F.S.A.), and Founder Console as related but separate products.

## Current consolidated state

The Web/PWA has been consolidated from verified prior EGM4000 builds and repository work. The merged build currently includes:

- C001 — cyber-aquatic responsive redesign foundations.
- C002 — first-run guided tutorial covering setup, session logging, analytics, evidence-labeled coaching, risk controls, community, survey privacy, and Research Lab safety.
- C004 — registered-user local prototype community with forum topics, blog posts, comments, reactions, reports, owner moderation, and moderation audit records.
- C005 — privacy-preserving first/returning visitor surveys with explicit consent/decline/erase controls, local pseudonymous visitor token, audience targeting, frequency caps, response storage, and owner-only local survey builder.
- Fire Kirin secure external login workflow.
- User-authorized browser screen feedback.
- Local session evidence logger, metrics, replay, and evidence-based coaching.
- JSON export/import and local persistence.
- PWA manifest and service-worker cache.

The following major requirements are **not complete** and must not be represented as production-ready: C003 production owner authentication, C006 dedicated session-derived Tips Center, C007 complete 100-feature Admin Panel, C008 complete A071-A095 monetization implementation, and C009 full R001-R049 return-feature/adoption implementation.

## What is included

- `android-egm4000/` — native Android project for EGM4000 Fire Kirin Companion.
- `web/` — consolidated local-first EGM4000 web/PWA public beta.
- `shared/` — normalized gameplay event schema plus machine-readable continuity manifest.
- `config/fire-kirin-portal.json` — configured Fire Kirin login portal used by Android and Web/PWA.
- `contracts/` — safe contracts for F.S.A. telemetry and Founder Console integration.
- `docs/` — safety, Fire Kirin companion, release ledger, project status, backlog, consolidation notes, and AI continuation documentation.
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
5. `docs/CONSOLIDATED_WEB_V5.md`
6. `docs/ai-continuation/README.md`

## AI continuation docs

Use these when continuing the project with another AI assistant:

- `docs/ai-continuation/README.md` — master handoff index.
- `docs/ai-continuation/PROJECT_STATUS_SV09.md` — historical status snapshot and known unfinished work.
- `docs/ai-continuation/SAFETY_BOUNDARIES.md` — non-negotiable safety rules.
- `docs/ai-continuation/NEXT_BUILD_PLAN.md` — next milestone plan.
- `docs/ai-continuation/UPLOAD_TO_GITHUB_INSTRUCTIONS.md` — GitHub build/upload workflow.
- `docs/ai-continuation/CHATGPT_CONTINUE_PROMPT.md` — prompt for ChatGPT.
- `docs/ai-continuation/COPILOT_CONTINUE_PROMPT.md` — prompt for GitHub Copilot.
- `docs/ai-continuation/GROK_CONTINUE_PROMPT.md` — prompt for Grok.
- `docs/ai-continuation/PERPLEXITY_CONTINUE_PROMPT.md` — prompt for Perplexity.

## Product boundaries

EGM4000, F.S.A., and Founder Console are related but separate products.

- **EGM4000**: analytics, coaching, replay, tips, normalized events, community, privacy-safe surveys, evidence labels.
- **F.S.A. / Fish Shooter Arcade**: separate owned virtual/non-cash fish-shooter game that can provide exact telemetry.
- **Founder Console**: separate owner/admin control plane for settings, safety, telemetry, moderation, surveys, and experiments.

Do not merge them into one unsafe product.

## Fire Kirin workflow

Configured Fire Kirin login portal:

`https://play.firekirin.xyz/web_game/firekirin777_pc/index.html`

EGM4000 does **not** create a fake Fire Kirin login and does **not** store Fire Kirin credentials.

The safe workflow is:

1. Open EGM4000.
2. Tap **Open Fire Kirin securely**.
3. EGM4000 opens the Fire Kirin portal externally.
4. Sign in directly with Fire Kirin in the browser or official app/site.
5. Return to EGM4000.
6. Start authorized screen feedback if desired.
7. Log session evidence.
8. Review EGM4000 feedback, replay, metrics, and tips.

## Safety boundary

EGM4000 does not guarantee profit, predict random outcomes, infer hidden server state, manipulate balances, bypass protections, or provide live-service cheating. It only explains authorized evidence and clearly labels estimates/hypotheses.

The Research Lab is limited to original/local sandbox software, owned or authorized test environments, reverse-engineering education, AI experiments, and defensive anti-cheat study.

## Build APK

Open GitHub → Actions → **Build EGM4000 Fire Kirin APK**. The output artifact is named:

`EGM4000-Fire-Kirin-Companion-debug-apk`

Inside that artifact is:

`app-debug.apk`

This is a debug/beta APK, not a Play Store production release.

## Web/PWA

Open `web/index.html` locally for most local-first features or host the `web/` folder on HTTPS. Browser screen feedback requires HTTPS and explicit user permission.

## Next build priorities

1. C003 — server-side sole-owner authentication boundary.
2. C006 — dedicated session-derived Tips Center with evidence/confidence display.
3. Continue C007 Admin 100 from verified partial state; do not mark incomplete features complete.
4. Implement C008 A071-A095 monetization capabilities within Admin 100.
5. Implement C009 R001-R049 with actual adoption/retention instrumentation.
6. Android Evidence Review v0.2 and Web/PWA parity hardening.
7. Shared schema validator, F.S.A. exact telemetry contract, signed Android release workflow, and device QA.
