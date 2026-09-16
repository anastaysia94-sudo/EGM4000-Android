# F.S.A. → EGM4000 live production verification

Date: 2026-09-16

This record documents a temporary, isolated production probe used to verify the already-deployed F.S.A. → EGM4000 consumer v2 and its automatic execution paths. All probe data was deleted after verification.

## What was verified

### Immediate trigger path

A temporary synthetic EGM identity was linked to a temporary F.S.A. player through the same Supabase Auth UUID. One F.S.A. telemetry session containing three source events was inserted:

- `session_start`
- `performance_sample` with `shots=17`, `hits=11`, `score=1234`
- `session_end`

The `egm_fsa_event_auto_import` `AFTER INSERT` trigger imported the events immediately into EGM4000.

Verified results:

- exactly one durable pseudonymous subject link;
- exactly one F.S.A. session link;
- exactly one EGM gameplay session;
- exactly three normalized EGM events;
- all normalized events grouped to the same gameplay-session ID;
- event aliases applied (`session_start` → `session_started`, `session_end` → `session_ended`);
- `source = fsa-supabase-v2`;
- `evidence_type = exact_telemetry`;
- `confidence = 1`;
- the normalized payload contained a stable SHA-256 `fsaPlayerKey` and did **not** contain the raw F.S.A. player UUID;
- the gameplay session received `shots=17` and `hits=11`;
- the two-minute source session closed as a two-minute EGM gameplay session;
- `starting_bankroll`, `spend`, and `payout` remained `NULL`;
- normalized payloads preserved `currencyBoundary = virtual_non_cash`.

### Idempotency / replay

The repair RPC was run again against the already-imported probe.

Verified result:

- `processed = 0`
- `remainingLinked = 0`
- `pendingUnlinked = 0`
- normalized-event count remained three;
- gameplay-session count remained one;
- subject-link count remained one;
- session-link count remained one.

This confirms replay/backfill does not duplicate canonical events or sessions.

### Scheduled catch-up path

A second temporary event was inserted while the synthetic EGM identity was deliberately marked inactive. The insert trigger therefore could not resolve an active EGM user and did not import the event.

The synthetic EGM identity was then reactivated. The next `pg_cron` execution of `egm-fsa-telemetry-import-v1` picked up the previously missed event and imported it through the same canonical v2 importer.

The repair job completed successfully on the 20:44 UTC tick. Subsequent scheduled runs also completed successfully.

This separately proves the intended two-layer automatic model:

`new linked event → immediate database trigger`

`missed / temporarily unlinked eligible event → minute-level cron repair`

## Cleanup proof

After verification, every probe row was removed from:

- `egm4000.normalized_events`
- `egm4000.fsa_session_links`
- `egm4000.fsa_subject_links`
- `egm4000.gameplay_sessions`
- `public.fsa_telemetry_events`
- `public.fsa_telemetry_sessions`
- `public.fsa_players`
- `public.fsa_agents`
- `public.fsa_distributors`
- `egm4000.users`

Post-cleanup checks returned zero remaining probe users, players, agents, distributors, source telemetry events, and normalized probe events.

## Final runtime state

After cleanup:

- `egm_fsa_event_auto_import` remained enabled on `public.fsa_telemetry_events`;
- `egm-fsa-telemetry-import-v1` remained active in `pg_cron`;
- recent cron executions remained successful;
- the repair RPC reported `processed=0`, `remainingLinked=0`, and `pendingUnlinked=0`;
- production returned to its pre-probe state with no F.S.A. source telemetry rows.

## Identity prerequisite

The consumer intentionally requires:

`public.fsa_players.auth_user_id = egm4000.users.auth_user_id`

and the matching EGM user must be active. This is an explicit identity/consent boundary, not a fuzzy username/email match. Existing seeded EGM content rows currently have no Supabase Auth UUIDs, so they are not automatically treated as real linked player identities.

## Security note

The bridge link tables themselves have RLS and restrictive backend-only policies. The broader legacy `egm4000` core schema still has tables with RLS disabled; current database privilege checks show `anon` and `authenticated` have no schema usage and no direct CRUD privilege there. RLS hardening for those legacy tables should remain a separate, policy-aware migration rather than being enabled blindly and breaking server behavior.
