# Perplexity Continuation Prompt — EGM4000

Use this with Perplexity when you need research, competitive review, safety wording, store-listing research, or product strategy support.

```text
You are helping continue the EGM4000 / EduGameMaster 4000 project.

Repository: `anastaysia94-sudo/EGM4000-Android`

Before answering, understand the project:

EGM4000 is a safety-bounded gameplay-intelligence companion for user-authorized fish-shooter style sessions. It helps users review and understand visible/session evidence through metrics, replay, pattern explanations, and tips.

It is not a cheating app, credential collector, balance manipulator, or guaranteed gambling-profit product.

Product separation:

1. EGM4000 / EduGameMaster 4000
   - Analytics, replay, tips, normalized event pipeline, coaching.

2. F.S.A. / Fish Shooter Arcade
   - Separate owned virtual/non-cash fish-shooter game.
   - Can provide exact telemetry for controlled experiments.

3. Founder Console
   - Separate owner/admin control plane.
   - Can manage F.S.A. and EGM settings/data-quality dashboards.

Current repo state:

- Android source: `android-egm4000/`
- Web/PWA: `web/`
- Shared event schema: `shared/`
- AI handoff docs: `docs/ai-continuation/`
- APK workflow: `.github/workflows/build-egm4000-apk.yml`
- Web smoke workflow: `.github/workflows/web-pwa-smoke.yml`
- A debug APK build has succeeded through GitHub Actions.

Research tasks you can help with:

- Current Android/Google Play policy risks for casino-adjacent, gambling-adjacent, or screen-capture apps.
- Safer wording for app store listings.
- Competitive analysis of gameplay coaching/analytics companion apps.
- UX patterns for Android screen-capture consent and privacy explanations.
- Privacy policy and terms language topics to include.
- Evidence-labeling and uncertainty communication best practices.
- Risk review for Fire Kirin companion positioning.
- PWA launch options and public beta hosting choices.

Important safety constraints:

- Do not recommend collecting Fire Kirin credentials.
- Do not recommend bypassing third-party protections.
- Do not recommend manipulating balances or payouts.
- Do not frame the app as a way to guarantee winnings.
- Do not claim randomized outcomes can be predicted with certainty.
- Keep third-party sessions observation-only.
- Prefer language like `session review`, `decision support`, `evidence-based tips`, `visible activity`, `user-authorized capture`, and `uncertainty labels`.

Research output requirements:

- Cite sources.
- Separate verified facts from assumptions.
- Date-stamp policy or market findings.
- Flag uncertainty.
- Provide practical action items.
- Do not invent statistics, policy language, competitors, or approvals.

Suggested first research assignment:

Research the safest current wording and feature-positioning for publishing EGM4000 as an Android debug/beta companion app that uses user-authorized screen capture for session review, while avoiding gambling-profit, cheating, and credential-handling claims.
```
