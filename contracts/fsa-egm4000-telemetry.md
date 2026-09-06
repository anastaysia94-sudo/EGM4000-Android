# F.S.A. → EGM4000 Telemetry Contract

Status: implemented bridge contract for the separate owned Fish Shooter Arcade product.

## Purpose

F.S.A. / Fish Shooter Arcade is a separate owned game. It can safely provide **exact telemetry** to EGM4000 because it is controlled by the project owner and does not require scraping, bypassing, guessing, or manipulating any third-party live-service game.

Canonical flow:

`PLAY F.S.A. -> F.S.A. emits exact virtual/non-cash telemetry -> authenticated bridge -> EGM4000 normalizes -> measures -> analyzes -> explains -> player reviews`

## Boundaries

F.S.A. remains a separate product/codebase from EGM4000. Shared schemas and the authenticated telemetry contract are the integration boundary.

F.S.A. telemetry is allowed because it comes from an owned, controlled environment. F.S.A. credits are virtual/non-cash by default.

Manual EGM4000 browser controls never become `exact_telemetry`, even if the user selects the F.S.A. adapter. Exact events are accepted only through the owned bridge.

## Authenticated bridge

Endpoint:

`POST /api/fsa/telemetry`

Required request header:

`X-EGM-FSA-Token: <server-configured EGM_FSA_TELEMETRY_TOKEN>`

The token is configured as a deployment secret and is never committed to source control. The bridge rejects requests when the secret is absent or incorrect.

The bridge also requires an active EGM4000 `userId`, keeps a durable mapping between the external F.S.A. session ID and the internal EGM4000 live-session ID, and relies on unique source event IDs to prevent duplicate ingestion.

Ordinary `POST /api/live/event` requests are explicitly rejected if they attempt to self-label an event as `exact_telemetry`.

## Required event envelope

Every event sent from F.S.A. to EGM4000 includes:

```json
{
  "sourceProduct": "fsa",
  "userId": 2,
  "sessionId": "session_example",
  "eventId": "evt_example",
  "eventType": "shot_fired",
  "occurredAt": "2026-09-06T09:00:00Z",
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

The ingestion adapter normalizes `credit_changed` to the canonical EGM4000 `credit_change` event type. Legacy Android aliases such as `shot`, `credit_up`, and `credit_down` are also normalized at the server ingestion boundary so Web, Android, and F.S.A. feed the same analysis vocabulary.

## Credit event payload

```json
{
  "eventType": "credit_changed",
  "evidenceLabel": "exact_telemetry",
  "confidence": 1,
  "payload": {
    "currencyType": "virtual_non_cash_credit",
    "creditDelta": -5,
    "balanceAfter": 940,
    "reason": "shot_fired"
  }
}
```

The bridge rejects F.S.A. credit events unless `currencyType` is `virtual_non_cash_credit`.

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

EGM4000 treats F.S.A. events as exact telemetry only when:

1. the request passes the owned bridge token check;
2. `sourceProduct` is `fsa`;
3. `evidenceLabel` is `exact_telemetry`;
4. confidence is exactly `1`;
5. the EGM4000 user exists and is active;
6. the session and event IDs are present;
7. timestamps are valid/ordered by the producer;
8. credit events explicitly identify virtual/non-cash currency.

Each accepted event flows through the same persisted core-loop engine used by authenticated Web and Android evidence. The response includes the EGM4000 live-session ID and current `egm.analysis.v1` analysis result.

## Fixture and CI proof

- `shared/fixtures/sample-fsa-exact-telemetry-session.json` — deterministic owned-F.S.A. fixture.
- `shared/validate-fixtures.js` — validates source, confidence, monotonic timestamps, event IDs, required event types, and virtual/non-cash credit semantics.
- `.github/workflows/integration-core-loop.yml` — validates the F.S.A. fixture and full-stack core loop on GitHub Actions.

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
