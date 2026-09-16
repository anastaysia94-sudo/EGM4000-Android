-- EGM4000 <- F.S.A. Supabase telemetry consumer v1
-- Server-only importer for the shared Supabase project.
--
-- Identity boundary:
--   public.fsa_players.auth_user_id -> egm4000.users.auth_user_id
-- Only active EGM4000 users are imported. Raw F.S.A. player UUIDs are not copied
-- into egm4000.normalized_events; a stable pseudonymous player key is stored instead.
--
-- Idempotency boundary:
--   normalized_events.source_event_id = 'fsa-supabase:' || fsa_telemetry_events.id
-- The existing unique source-event index makes retries duplicate-safe.

create or replace function public.egm_rpc_import_fsa_telemetry(
  p_limit integer default 200
)
returns jsonb
language plpgsql
security definer
set search_path = pg_catalog, public, egm4000, extensions
as $$
declare
  batch_limit integer := least(greatest(coalesce(p_limit, 200), 1), 1000);
  imported_count integer := 0;
  remaining_linked_count bigint := 0;
  unlinked_count bigint := 0;
begin
  insert into egm4000.normalized_events(
    user_id,
    source_event_id,
    event_time,
    platform,
    event_type,
    source,
    evidence_type,
    confidence,
    payload
  )
  select
    u.id,
    'fsa-supabase:' || e.id::text,
    e.occurred_at,
    'fsa',
    case e.event_type
      when 'session_start' then 'session_started'
      when 'session_end' then 'session_ended'
      when 'power_used' then 'powerup_used'
      else e.event_type
    end,
    'fsa-supabase-v1',
    'exact_telemetry',
    1,
    coalesce(e.payload, '{}'::jsonb) || jsonb_strip_nulls(jsonb_build_object(
      'fsaSessionId', e.session_id::text,
      'fsaPlayerKey', encode(extensions.digest(e.player_id::text || ':fsa-egm4000-v1', 'sha256'), 'hex'),
      'gameId', e.game_id,
      'room', e.room,
      'producerSource', e.source
    ))
  from public.fsa_telemetry_events e
  join public.fsa_players fp
    on fp.id = e.player_id
  join egm4000.users u
    on u.auth_user_id = fp.auth_user_id
   and u.status = 'active'
  where not exists (
    select 1
    from egm4000.normalized_events n
    where n.source_event_id = 'fsa-supabase:' || e.id::text
  )
  order by e.id asc
  limit batch_limit
  on conflict do nothing;

  get diagnostics imported_count = row_count;

  select count(*) into remaining_linked_count
  from public.fsa_telemetry_events e
  join public.fsa_players fp
    on fp.id = e.player_id
  join egm4000.users u
    on u.auth_user_id = fp.auth_user_id
   and u.status = 'active'
  where not exists (
    select 1
    from egm4000.normalized_events n
    where n.source_event_id = 'fsa-supabase:' || e.id::text
  );

  select count(*) into unlinked_count
  from public.fsa_telemetry_events e
  join public.fsa_players fp
    on fp.id = e.player_id
  left join egm4000.users u
    on u.auth_user_id = fp.auth_user_id
   and u.status = 'active'
  where u.id is null
    and not exists (
      select 1
      from egm4000.normalized_events n
      where n.source_event_id = 'fsa-supabase:' || e.id::text
    );

  return jsonb_build_object(
    'schema', 'egm.fsa-supabase-import.v1',
    'imported', imported_count,
    'remainingLinked', remaining_linked_count,
    'pendingUnlinked', unlinked_count,
    'batchLimit', batch_limit,
    'identityRule', 'shared_auth_user_id_active_egm_user',
    'idempotencyRule', 'fsa-supabase:<event_id>'
  );
end;
$$;

-- SECURITY DEFINER functions receive EXECUTE from PUBLIC by default. Remove that
-- default and make this import path server-only. The service-role credential must
-- never be shipped to the web/PWA or Android client.
revoke all on function public.egm_rpc_import_fsa_telemetry(integer)
  from public, anon, authenticated;
grant execute on function public.egm_rpc_import_fsa_telemetry(integer)
  to service_role;

comment on function public.egm_rpc_import_fsa_telemetry(integer) is
  'Server-only duplicate-safe importer from owned F.S.A. telemetry into EGM4000 normalized events. Links identities through shared Supabase Auth UUID and never copies raw F.S.A. player UUIDs into EGM event payloads.';
