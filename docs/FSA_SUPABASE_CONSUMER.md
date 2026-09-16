# F.S.A. Supabase → EGM4000 consumer

Status: **consumer v2 production migration applied; automatic trigger + database-internal repair scheduler; isolated PostgreSQL end-to-end CI gate.**

## Why this exists

F.S.A. has a hardened Supabase telemetry producer in the shared project. EGM4000 also has an older token-authenticated HTTP bridge, but telemetry already stored by the owned F.S.A. backend needs a database-native consumer so exact owned-game evidence can flow into EGM4000 without putting privileged credentials in a browser or Android client.

This consumer does **not** delete the older HTTP bridge. It is the canonical path for telemetry produced by the shared F.S.A. Supabase backend.

## Final v2 flow

`F.S.A. authenticated player → fsa_telemetry_sessions/events → shared Auth UUID match → durable pseudonymous subject link → one EGM gameplay session per F.S.A. session → exact normalized events → EGM analytics/coaching`

The identity rule is deliberately conservative:

`public.fsa_players.auth_user_id = egm4000.users.auth_user_id`

and the EGM4000 user must be active. Missing links stay pending. The consumer never guesses from username, email, display name, or another mutable field.

## Durable pseudonymous identity

`egm4000.fsa_subject_links` stores a stable SHA-256 `player_key`, never the raw F.S.A. player UUID in EGM normalized payloads. The link records the active EGM user resolved through the shared Supabase Auth UUID.

`egm4000.fsa_session_links` maps each F.S.A. telemetry session to exactly one `egm4000.gameplay_sessions` row. That gives EGM4000 a session-level unit for replay, metrics, analysis, and coaching instead of leaving F.S.A. events as an ungrouped stream.

Both link tables have RLS enabled and explicit restrictive backend-only policies. `anon` and `authenticated` have no direct access.

## Automatic ingestion

`egm_fsa_event_auto_import` is an `AFTER INSERT` trigger on `public.fsa_telemetry_events`. For a linked active user it immediately:

1. creates or reuses the pseudonymous subject link;
2. creates or reuses the EGM gameplay-session link;
3. normalizes the event with platform `fsa`, evidence type `exact_telemetry`, confidence `1`, and source `fsa-supabase-v2`;
4. assigns the linked gameplay-session ID to `normalized_events.live_session_id` so the session is analyzable as a unit;
5. copies only approved telemetry context into the payload, including the pseudonymous player key, F.S.A. session ID, game ID, room and producer source;
6. updates session shots/hits from bounded numeric performance samples;
7. closes the gameplay session when F.S.A. emits `session_end`.

## Financial boundary

F.S.A. credits are virtual/non-cash evidence. The consumer therefore creates gameplay sessions with:

- `starting_bankroll = NULL`
- `spend = NULL`
- `payout = NULL`

Normalized payloads are tagged `currencyBoundary = virtual_non_cash`. The consumer must not reinterpret F.S.A. credits as money or manufacture financial outcomes.

## Idempotency

Each source event uses:

`fsa-supabase:<event_id>`

as `normalized_events.source_event_id`. The existing unique partial index plus v2 upsert behavior means replaying/backfilling the same event updates its canonical normalized row instead of creating duplicates.

## Repair / catch-up RPC

`public.egm_rpc_import_fsa_telemetry(p_limit integer default 200)` remains the trusted repair path. In v2 it scans for linked events that are missing, lack a session link, or still use the v1 source and reprocesses them through the same canonical event importer.

Execute permission is intentionally narrow:

- `anon`: denied
- `authenticated`: denied
- `service_role`: allowed

Never put a service-role credential in Web/PWA or Android code.

## Database scheduler

`20260916_egm_fsa_consumer_scheduler_v1.sql` registers `egm-fsa-telemetry-import-v1` with `pg_cron` once per minute. Under v2 it is **repair insurance**, not the normal ingestion path. New linked events arrive through the trigger immediately; cron catches anything that was pending or needs canonical v2 repair.

The scheduler runs inside Postgres and stores no browser/API bearer credential. Cron-management privileges remain unavailable to ordinary application roles.

## Event vocabulary

Compatibility aliases are intentionally small:

- `session_start` → `session_started`
- `session_end` → `session_ended`
- `power_used` → `powerup_used`

Other F.S.A. producer names remain intact rather than pretending distinct concepts are equivalent.

## Verification

The dedicated `F.S.A. → EGM4000 Supabase Consumer v2` GitHub Actions workflow boots an isolated PostgreSQL 16 service, recreates the minimal production table/role contracts, applies the exact migration, inserts a deterministic F.S.A. session, and proves:

- one pseudonymous subject link;
- one F.S.A. session → one EGM gameplay session;
- three source events → exactly three normalized events even after replay;
- shots/hits propagate to the gameplay session;
- bankroll/spend/payout stay NULL;
- exact-telemetry evidence and confidence remain intact;
- every event is grouped to the mapped gameplay session;
- the virtual/non-cash boundary survives normalization;
- RLS is enabled on bridge-link tables;
- ordinary API roles cannot execute the repair RPC;
- `service_role` can execute it.

Production currently has no real F.S.A. telemetry rows, so the live importer correctly reports zero processed, zero remaining linked and zero pending unlinked. We do not inject fake production telemetry merely to manufacture an exciting dashboard.

## Operational interpretation

When the first real linked F.S.A. player produces telemetry, no manual bridge action should be required: the insert trigger performs the consumer step in the same database transaction. The cron job remains the recovery/backfill layer. If an event is unlinked, fix the explicit identity relationship instead of assigning it to a convenient-looking EGM user.

EGM4000 may analyze these owned exact events for behavior, replay, pacing, accuracy and coaching. It still must not claim guaranteed winnings, infer hidden third-party server state, or convert virtual/non-cash telemetry into real-money outcomes.
