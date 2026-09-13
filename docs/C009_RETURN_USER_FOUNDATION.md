# C009 — Return-user foundation and Evidence Lab checkpoint

Date: 2026-09-13

C009 is complete. The return-user registry now contains canonical R001–R049 names with 49 verified implemented features and 0 modelled features. Implementation status is backed by end-user behavior, persistence, authenticated APIs, feature-usage events, and dedicated CI rather than placeholder rows or assumed adoption.

## Completed return-user surface

The original foundation remains in place:

- Authenticated personalized Today dashboard.
- One-tap session start and quick recap.
- Session-derived personalized tips and tip history.
- Daily insight and seven-day/prior-week performance story.
- Session and game comparisons.
- Bankroll guard, variance explainer, confidence meter, and evidence drawer.
- What-changed feed and healthy evidence-tracking streaks.
- Ask-EGM data questions and metric explanations.
- Universal search, cross-device persisted state, installable PWA, and offline capture.
- Evidence-linked notification center.
- Community feed, followed topics, bookmarks/saved tips, and private profile controls.
- Authorized research sandbox and experiment journal.
- Contextual feature discovery.
- Rolling 30-day personal evidence report.
- CSRF-protected first-party feature-usage events.
- Owner-only per-feature event, unique-user, and last-used adoption reporting.
- Synthetic seed users excluded from real-user adoption denominators.

The remaining 19 features were converted from modelled entries into the persisted **My Evidence Lab** workspace:

- R006 tip usefulness rating.
- R009 personal best tracker based on recorded evidence.
- R012 target-efficiency board.
- R013 weapon/cost efficiency.
- R014 denomination comparison.
- R015 time-of-session analysis.
- R016 duration-based fatigue safeguard.
- R018 responsible-play pause that blocks session tools while active.
- R023 goals limited to evidence review, reflection, and evidence-consistency behaviors.
- R024 goal progress.
- R025 healthy tracking streaks remain evidence-oriented rather than gambling-reward oriented.
- R026 learning achievements.
- R027 personal missions limited to learning/evidence behaviors.
- R028 coach inbox.
- R031 screenshot intake.
- R032 video review workspace.
- R033 voice/audio session notes plus optional transcript/reflection notes.
- R034 smart tags.
- R035 saved evidence views.
- R041 notification controls.

## Persistence and authenticated APIs

`fullstack/return_workspace.py` owns the C009 workspace data model and evidence-derived summaries. It creates/preserves:

- `return_tip_feedback`
- `return_goals`
- `return_preferences`
- `return_notes`
- `return_media`
- `return_saved_views`

Authenticated/CSRF-protected surfaces include:

- `GET /api/return/workspace`
- `GET /api/return/media?id=<id>` with user ownership enforcement
- `POST /api/return/tip-rating`
- `POST /api/return/goal`
- `POST /api/return/preferences`
- `POST /api/return/pause`
- `POST /api/return/note`
- `POST /api/return/saved-view`
- `POST /api/return/media`
- `POST /api/return/media-review`

Media intake has explicit type/size limits and lightweight signature validation. Supported evidence media are screenshots, short review videos, and voice/audio notes. Media is stored in the authenticated persistent datastore instead of an unauthenticated public filesystem.

## Safety boundaries

C009 analytics describe only user-authorized recorded history. Personal bests, target/weapon/denomination comparisons, time-of-session summaries, and coaching ratings are descriptive evidence views, not predictions of random outcomes or proof of future profit.

Responsible-play controls are deliberately asymmetric: the user can pause session tools, and the application does not override that pause to increase engagement. Goals, achievements, and missions reward evidence review, reflection, learning, and safer tracking rather than wager volume, session length, spend, or payout.

No adoption percentage is seeded, fabricated, or guaranteed. Feature usage is measured from real first-party events, with synthetic accounts excluded from real-user adoption counts.

## Verification

Code checkpoint: `cf93c32a3f8eaa8e422839162fab01e3f55e6146` (`Fix C009 PostgreSQL-safe goal aggregation`), following implementation commit `7d33d5beab69077be02e33eaf981ee605f644575`.

Dedicated workflow: `.github/workflows/return-features-smoke.yml` (`EGM4000 C009 Return User Lab`).

Verified successfully on GitHub Actions:

- Python module compilation and assembled server syntax.
- JavaScript syntax of the assembled public app.
- R001–R049 registry integrity: 49 implemented / 0 modelled.
- Fresh real-owner evidence fixture.
- Authenticated `GET /api/return/workspace` analytics.
- CSRF-protected tip rating, safe goals, notification controls, pause controls, reflection notes, voice transcripts, and saved views.
- Screenshot, video, and voice media upload validation and authenticated retrieval.
- Media review persistence and smart-tag generation.
- PostgreSQL/Supabase compatibility smoke.
- Fullstack smoke.
- Core-loop integration regression suite.
- Portable production-style Docker smoke.

C009 completion does not mean the whole EGM4000 product is production-complete. Production auth/deployment hardening, physical Android/public deployment QA, remaining Admin 100 work, and provider-dependent monetization work retain their own milestones and evidence requirements.
