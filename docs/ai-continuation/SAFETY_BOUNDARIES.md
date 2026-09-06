# EGM4000 Safety Boundaries

This project is allowed to build coaching, analytics, telemetry, replay, and educational tools. It is not allowed to become a tool for cheating, credential theft, hidden-state extraction, or guaranteed gambling outcomes.

## Allowed

EGM4000 may:

- Open a third-party game site/app externally so the user signs in directly with that service.
- Let the user manually start/stop authorized screen observation.
- Use Android screen-capture permission only after the system permission prompt.
- Process captured frames locally for aggregate signals.
- Discard raw screenshots/frames unless the user explicitly exports them.
- Store local session events, timestamps, notes, and visible metrics.
- Analyze user-entered outcomes.
- Analyze owned F.S.A. game telemetry.
- Generate evidence-labeled feedback.
- Calculate session pace, duration, drawdown, break reminders, and basic behavioral patterns.
- Explain uncertainty.
- Export/import normalized gameplay event bundles.

## Not allowed

EGM4000 must not:

- Ask for, collect, store, forward, or replay Fire Kirin credentials.
- Create a fake Fire Kirin login screen.
- Intercept tokens, cookies, session IDs, passwords, or payment data.
- Bypass app/site security controls.
- Manipulate real balances, credits, payouts, bets, deposits, withdrawals, or accounts.
- Promise profit, guaranteed winnings, or guaranteed cashout.
- Claim to know hidden random number generator state.
- Predict randomized outcomes with certainty.
- Automate prohibited gameplay actions against third-party systems.
- Scrape private third-party data without authorization.
- Present estimates as facts.
- Hide uncertainty from the user.

## Fire Kirin companion rule

The safe Fire Kirin flow is:

1. User opens EGM4000.
2. User taps `Open Fire Kirin`.
3. EGM4000 opens Fire Kirin in the user's browser or the official app/site.
4. User signs in directly with Fire Kirin.
5. User returns to EGM4000.
6. User starts screen feedback with Android's system screen-capture consent.
7. EGM4000 analyzes visible/session-level activity only.
8. EGM4000 labels every tip with evidence type and confidence.

## Evidence language

Use this language:

- `Exact telemetry` for owned/F.S.A. telemetry or explicit instrumentation.
- `Observed` for visible screen/session events.
- `Estimated` for inferred values from screen activity.
- `Correlated` for patterns that moved together in past data.
- `Hypothesis` for a possible explanation that needs more data.
- `Unknown` when not enough evidence exists.

Avoid this language:

- `Guaranteed`
- `Will win`
- `Profit lock`
- `Cashout sure thing`
- `RNG cracked`
- `Hidden pattern detected` unless there is actual authorized evidence and the claim is narrowed.

## UI warnings that should remain visible

EGM4000 should clearly say:

- `EGM4000 is an analysis and coaching tool, not a guarantee of results.`
- `Third-party sessions are observation-only.`
- `EGM4000 does not collect game passwords or control your account.`
- `Randomized outcomes cannot be predicted with certainty.`
- `Take breaks and set limits.`

## Reviewer checklist

Before merging new code, ask:

- Does this feature require user consent?
- Does it handle credentials safely?
- Does it separate exact telemetry from estimates?
- Does it avoid profit guarantees?
- Does it avoid manipulating third-party systems?
- Does it keep EGM4000, F.S.A., and Founder Console distinct?
