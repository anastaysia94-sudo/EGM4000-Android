# F.S.A. → EGM4000 Telemetry Contract

Status: draft contract for the separate owned Fish Shooter Arcade product.

## Purpose

F.S.A. / Fish Shooter Arcade is a separate owned game. It can safely provide **exact telemetry** to EGM4000 because it is controlled by the project owner and does not require scraping, bypassing, guessing, or manipulating any third-party live-service game.

Canonical flow:

`PLAY F.S.A. -> F.S.A. emits exact virtual/non-cash telemetry -> EGM4000 ingests -> EGM4000 measures -> EGM4000 explains -> player reviews`

## Boundaries

F.S.A. must remain a separate product/codebase from EGM4000.

F.S.A. telemetry is allowed because it comes from an owned, controlled environment.

F.S.A. should be virtual/non-cash by default. Do not represent F.S.A. virtual credits as redeemable cash unless a future legal/compliance layer explicitly supports that.

## Required event envelope

Every event sent from F.S.A. to EGM4000 should include:

```json
{
  "schema": "egm4000.gameplay-event.v1",
  "sourceProduct": "fsa",
  "sessionId": "session_example",
  "eventId": "evt_example",
  "playerId": "local_or_pseudonymous_player_id",
  "platform": "Fish Shooter Arcade",
  "eventType": "shot",
  "occurredAt": "2026-09-05T17:05:00-07:00",
  "evidenceLabel": "exact_telemetry",
  "confidence": 1,
  "payload": {}
}
```

## Required F.S.A. event types

- `session_started`
- `session_ended`
- `round_started`
- `round_ended`
- `shot_fired`
- `target_spawned`
- `target_hit`
- `target_missed`
- `boss_spawned`
- `boss_hit`
- `boss_defeated`
- `credit_changed`
- `powerup_collected`
- `powerup_used`
- `difficulty_changed`
- `break_prompt_shown`

## Credit event payload

```json
{
  "eventType": "credit_changed",
  "evidenceLabel": "exact_telemetry",
  "confidence": 1,
  "payload": {
    "currencyType": "virtual_non_cash_credit",
    "delta": -5,
    "balanceAfter": 940,
    "reason": "shot_fired"
  }
}
```

## Shot event payload

```json
{
  "eventType": "shot_fired",
  "evidenceLabel": "exact_telemetry",
  "confidence": 1,
  "payload": {
    "weaponLevel": 3,
    "aimX": 0.52,
    "aimY": 0.37,
    "targetId": "fish_219",
    "cost": 5
  }
}
```

## EGM4000 ingestion behavior

EGM4000 may treat F.S.A. events as exact telemetry when:

1. the event comes from an owned F.S.A. build;
2. the event validates against the shared schema;
3. the session ID is stable;
4. timestamps are monotonic or explainable;
5. the data is virtual/non-cash by default.

## What EGM4000 may say

Allowed:

- "Your shot pace increased after the boss spawned."
- "Your virtual-credit spend rate rose during this round."
- "In this owned F.S.A. session, this is exact telemetry."
- "This pattern is a review signal, not a prediction."

Not allowed:

- "This guarantees a win."
- "Use this to beat Fire Kirin."
- "This reveals hidden RNG/server behavior."
- "This manipulates third-party credits."
