# EGM4000 Next Build Plan

This file tells any AI assistant what to build next without losing the project's progress.

## Goal

Turn the current debug APK and web/PWA foundation into a stronger beta product that can be used, tested, and improved without breaking safety boundaries.

## Highest-priority next milestone

**Milestone BETA-01: Local Session Engine**

Build a reliable local session system shared conceptually between Android and web.

### Deliverables

1. `Session` model
   - `sessionId`
   - `gameProfile`
   - `startedAt`
   - `endedAt`
   - `source`
   - `status`
   - `notes`
   - `riskFlags`

2. `GameplayEvent` model
   - Follow `shared/normalized-gameplay-event.schema.json`.
   - Preserve `evidenceClass` and `confidence`.

3. Local persistence
   - Android: Room or DataStore.
   - Web: localStorage/IndexedDB.
   - Do not require cloud accounts for beta.

4. Session timeline
   - Show events in chronological order.
   - Show evidence class badges.
   - Show confidence.
   - Show visible warnings when data is incomplete.

5. Tips engine
   - Generate tips from actual logged events only.
   - Tips must include evidence class, confidence, and reason.
   - Do not generate profit promises.

6. Import/export
   - Export normalized session JSON.
   - Import exported JSON for replay/review.
   - Validate schema and reject malformed data.

7. Test fixtures
   - Include at least 3 sample sessions:
     - Fire Kirin observation-only session.
     - F.S.A. exact telemetry session.
     - Manual user-entry session.

8. CI checks
   - Android debug build.
   - Basic unit tests for event validation.
   - Web smoke test.

## Next milestone after BETA-01

**Milestone BETA-02: Replay + Pattern Lab**

Build:

- Timeline replay controls.
- Pattern cards.
- Confidence warnings.
- Sample-size warnings.
- Correlation calculations.
- Exportable replay report.

## Next milestone after BETA-02

**Milestone BETA-03: F.S.A. Controlled Telemetry Bridge**

Build:

- Separate F.S.A. owned game telemetry feed.
- Exact event generation from owned game state.
- EGM4000 ingestion of owned exact telemetry.
- Comparison between exact F.S.A. telemetry and screen-observed estimates.
- Validation report.

## Next milestone after BETA-03

**Milestone BETA-04: Founder Console Lite**

Build:

- Separate admin route/app.
- Local owner gate for beta.
- Settings dashboard.
- Virtual credits/settings controls for F.S.A. only.
- EGM data-quality dashboard.
- No third-party account/balance mutation.

## Definition of done for each milestone

A milestone is not done until:

- Code is committed to GitHub.
- Android build workflow passes.
- Web smoke test passes when web is affected.
- README or docs are updated.
- Safety boundaries are preserved.
- User-facing language avoids guarantees or cheating claims.

## Avoid

- Do not rebuild from scratch unless the repo is corrupted.
- Do not delete the web/PWA progress.
- Do not merge F.S.A. into EGM4000.
- Do not add credential collection.
- Do not fake tests.
- Do not claim a feature is complete without code and CI evidence.
