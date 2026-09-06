# EGM4000 Consolidated Web/PWA v5

Date: 2026-09-05
Status: authoritative Web/PWA consolidation checkpoint

## Purpose

This checkpoint merges verified EGM4000 additions from prior local/self-contained builds into the GitHub Web/PWA without replacing the native Android project or collapsing EGM4000, Fish Shooter Arcade, and Founder Console into one product.

## Verified merged features

### C001 — Visual redesign foundations
- Cyber-aquatic responsive interface direction.
- Mobile/tablet/desktop responsive layout.
- Stronger dashboard hierarchy and local-first interaction patterns.

### C002 — First-time guided tutorial
- Nine-step first-run tutorial.
- Covers platform context, session logging, analytics, evidence/confidence, AI coaching boundaries, bankroll/risk controls, community, survey privacy, and Research Lab safety.
- Persists seen/completed state locally and can be reopened.

### C004 — Community forum + blog
- Registered local-prototype users.
- Forum topics and blog posts.
- Comments.
- Useful / Insightful reactions.
- Reports and duplicate-open-report protection.
- Owner moderation queue.
- Hide / restore / dismiss workflows.
- Moderation audit records.
- User-generated community claims remain separate from verified gameplay evidence.

### C005 — Privacy-preserving surveys
- Explicit allow / decline / erase controls.
- First-vs-returning visitor classification on device.
- Consent-gated pseudonymous local token.
- First / returning / all audience targeting.
- Frequency caps and impression limits.
- Local response storage.
- Owner-only local survey builder gate.
- Production contract requires server-side sole-owner authorization, secure sessions, CSRF protection, rate limiting, validation, audit logging, retention controls, and privacy review.

## Repository features preserved during consolidation

- Fire Kirin external login portal workflow.
- No Fire Kirin password collection or storage.
- User-authorized browser screen feedback with browser permission.
- Local session evidence logger.
- Metrics, replay, and evidence-based coaching.
- JSON export / import.
- PWA manifest and service worker.
- Android project and APK build workflow remain separate and intact.
- F.S.A. telemetry and Founder Console contracts remain separate.

## Canonical implementation-status rule

A requested feature is not considered complete merely because it appears in a checklist or design model. Only features with verified working implementation evidence should be marked complete.

### Complete in this consolidation
- C001
- C002
- C004
- C005

### Explicitly incomplete / partial
- C003 — production sole-owner authentication. Local prototype role checks are not production authentication.
- C006 — dedicated session-derived Tips Center. Existing coaching/tips are foundations, not the complete dedicated center.
- C007 — 100-feature owner Admin Panel. The canonical Admin 100 model exists and several community/survey capabilities have verified implementations, but the panel as a whole is incomplete.
- C008 — exactly 25 monetization capabilities A071-A095. They exist in the canonical model but are not all end-to-end implemented.
- C009 — R001-R049 return-user features and adoption/retention instrumentation. The canonical model exists but full implementation is incomplete.

## Verified Admin 100 portions inherited from prior builds

The historical Admin 100 evidence records the following as fully implemented foundations through C004/C005:

- A016 — user report queue.
- A019 — forum post moderation.
- A020 — blog comment moderation.
- A046 — survey builder.
- A047 — unique/first-visitor survey targeting.
- A048 — returning-user survey targeting.
- A055 — survey consent/privacy controls.

Partial admin workflows such as moderation case workspace, dedicated comment moderation queue, survey response review, mobile founder mode, and configuration backup/restore remain partial and must stay labeled as such until completed and tested.

## Security boundary

The Web/PWA is a local/mock prototype for account, owner, moderation, and survey state. Production must move privileged authorization and shared data to a backend with password hashing, secure HTTP-only cookies/sessions, CSRF protection, rate limiting, audit logs, account recovery controls, input validation, abuse controls, and least-privilege authorization.

No production credentials or third-party account secrets belong in frontend source.

## Next engineering order

1. C003 server-side owner authentication boundary.
2. C006 dedicated Tips Center derived from monitored session evidence with provenance/confidence display.
3. Continue C007 Admin 100 from verified partial state.
4. Complete C008 A071-A095 within Admin 100.
5. Implement C009 R001-R049 with actual feature-adoption and retention measurement.
6. Bring Android and Web/PWA feature parity forward without weakening third-party credential or safety boundaries.
