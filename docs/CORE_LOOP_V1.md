# EGM4000 Core Loop v1

Status: implemented as a safe local-first web workbench and reusable browser analysis engine.

## Product loop

WATCH → MEASURE → EXPLAIN → IMPROVE → MEASURE AGAIN

1. WATCH / RECORD
   - Accept user-recorded events or exact telemetry from owned/authorized systems.
   - Normalize each event to `egm.event.v1`.
   - Preserve provenance, evidence type, timestamp, platform, session ID, and confidence.

2. MEASURE
   - Event count
   - Shots
   - Breaks
   - Net recorded credit movement
   - Positive / negative credit events
   - Session duration
   - Shots per minute
   - Credit movement volatility
   - Maximum observed drawdown
   - Evidence completeness and reliability

3. EXPLAIN
   - Detect only patterns supported by recorded evidence.
   - Current v1 detectors include negative recorded net movement, increased pace alongside weaker recorded results, meaningful drawdown, long sessions without a break, and stable-pace descriptive correlation.
   - Every pattern carries evidence, confidence, and an explicit explanation that it is not a hidden-state or future-outcome prediction.

4. IMPROVE
   - Generate behavioral coaching tied to a measurable target.
   - Coaching examples: pace guardrail, drawdown stop-and-review trigger, scheduled break, or repeat-baseline recommendation.
   - Each recommendation includes evidence label, confidence, measurement target, and safety statement.

5. MEASURE AGAIN
   - Save a baseline analysis.
   - Record a new comparable session.
   - Compare changes in shots/minute, credit net, maximum drawdown, breaks, and evidence completeness.
   - Mark the selected coaching measurement as improved, worsened, unchanged, or insufficient evidence.

## Files

- `web/egm-core-loop.js` — reusable zero-dependency core engine.
- `web/core-loop.html` — interactive local-first Core Loop workbench.
- `shared/egm4000.normalized-event.v1.schema.json` — existing normalized event contract.
- `shared/egm4000.analysis.v1.schema.json` — analysis result contract.

## Safety boundary

This engine does not guarantee profit, predict random outcomes, infer hidden third-party server state, manipulate balances, bypass protections, or provide unauthorized live-service cheating. Credit movement is treated as a recorded metric only. Correlations are labeled as correlations. Exact telemetry is only exact when supplied by an owned or authorized source such as F.S.A.

## Next integration work

1. Add a Core Loop entry point from the consolidated `web/index.html` dashboard.
2. Feed Android Evidence Review events through the same normalized-event semantics.
3. Add JSON Schema validation in CI.
4. Connect F.S.A. exact telemetry to `egm.event.v1` through the existing safe telemetry contract.
5. Persist comparable sessions behind authenticated server storage when production auth exists.
6. Surface these analysis/coaching records in the dedicated C006 Tips Center.
