# F.S.A. Supabase -> EGM4000 consumer

Status: live database migration applied and repository migration staged on `egm-fsa-supabase-consumer-v1`.

## Why this exists

F.S.A. now has a hardened Supabase telemetry producer in the shared project. EGM4000 already has an older token-authenticated HTTP bridge, but the Supabase telemetry stream needed a separate consumer boundary so owned-game telemetry can flow into `egm4000.normalized_events` without weakening client access controls.

This consumer does **not** replace the HTTP bridge. It adds a second, server-only ingestion path for telemetry already stored by the owned F.S.A. backend.

## Import RPC

`public.egm_rpc_import_fsa_telemetry(p_limit integer default 200)`

The function:

1. reads F.S.A. telemetry events from the shared Supabase project;
2. links an F.S.A. player to an EGM4000 user only when both records share the same Supabase Auth UUID;
3. requires the EGM4000 user to be active;
4. writes normalized events with platform `fsa`, source `fsa-supabase-v1`, evidence type `exact_telemetry`, and confidence `1`;
5. uses `fsa-supabase:<event_id>` as the normalized source-event ID so retries are duplicate-safe;
6. stores the external F.S.A. session ID and a stable pseudonymous player key in the normalized payload;
7. does not copy the raw F.S.A. player UUID into EGM4000 normalized payloads;
8. returns import counts, remaining linked events, and pending unlinked events.

## Permission boundary

The RPC is `SECURITY DEFINER`, so its execute grants are intentionally narrow:

- `anon`: denied
- `authenticated`: denied
- `service_role`: allowed

Never place a service-role credential in the web/PWA or Android app. Invoke this RPC only from a trusted server, protected automation, or an administrative backend.

## Identity rule

The bridge is intentionally conservative:

`public.fsa_players.auth_user_id = egm4000.users.auth_user_id`

If that relationship is missing, the event is not imported. The function reports those events as `pendingUnlinked` instead of guessing a user from username, email, display name, or another mutable field.

## Duplicate rule

The importer creates normalized source IDs like:

`fsa-supabase:12345`

`egm4000.normalized_events` already has a unique partial index on `source_event_id`, and the importer also checks for an existing source ID before insertion. Re-running the same batch is therefore idempotent.

## Event vocabulary

The importer performs only three compatibility aliases:

- `session_start` -> `session_started`
- `session_end` -> `session_ended`
- `power_used` -> `powerup_used`

Other F.S.A. telemetry event names are preserved so EGM4000 does not pretend two different producer concepts are equivalent.

## Current live verification

At implementation time the live F.S.A. telemetry tables contained no events, so production verification was deliberately limited to the empty path. The live RPC returned:

- `imported: 0`
- `remainingLinked: 0`
- `pendingUnlinked: 0`

Permission checks also confirmed that anonymous and ordinary authenticated roles cannot execute the function while `service_role` can.

No synthetic telemetry was inserted into the live project merely to make a test look exciting.

## Operational call

From a trusted server using the Supabase service role:

```js
const { data, error } = await supabase.rpc('egm_rpc_import_fsa_telemetry', {
  p_limit: 200
});
```

Run repeatedly until `remainingLinked` reaches zero. If `pendingUnlinked` is non-zero, fix the account-linking relationship instead of forcing those events onto an arbitrary EGM4000 user.

## Remaining production proof

Once the first real linked F.S.A. player emits telemetry, verify all of the following from real records:

- one F.S.A. event creates one normalized EGM4000 event;
- the shared Auth UUID resolves to the intended active EGM4000 user;
- a retry imports zero duplicates;
- the normalized payload contains `fsaPlayerKey` but not the raw F.S.A. player UUID;
- events for an unlinked player remain unimported and increase `pendingUnlinked`;
- analysis consuming the normalized event preserves the `exact_telemetry` evidence label and does not turn telemetry into outcome guarantees.
