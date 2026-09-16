-- EGM4000 consumer v2 for the owned F.S.A. Supabase telemetry producer.
-- Final-state goals:
--   * shared-auth identity becomes a durable pseudonymous subject link
--   * each F.S.A. telemetry session maps to one EGM4000 gameplay session
--   * normalized events are idempotent and grouped by that gameplay session
--   * future F.S.A. events ingest automatically through a database trigger
--   * the backfill RPC repairs/imports earlier linked events safely
--   * bankroll/spend/payout remain NULL: F.S.A. telemetry is virtual/non-cash evidence

create table if not exists egm4000.fsa_subject_links (
  player_key text primary key,
  user_id bigint not null references egm4000.users(id) on delete cascade,
  link_source text not null default 'shared_auth_user_id',
  linked_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  constraint egm_fsa_player_key_format check (player_key ~ '^[0-9a-f]{64}$'),
  constraint egm_fsa_link_source_check check (link_source in ('shared_auth_user_id'))
);

create index if not exists idx_egm_fsa_subject_user
  on egm4000.fsa_subject_links(user_id);

create table if not exists egm4000.fsa_session_links (
  fsa_session_id uuid primary key,
  player_key text not null references egm4000.fsa_subject_links(player_key) on delete cascade,
  user_id bigint not null references egm4000.users(id) on delete cascade,
  gameplay_session_id bigint not null references egm4000.gameplay_sessions(id) on delete cascade,
  linked_at timestamptz not null default now(),
  unique (gameplay_session_id)
);

create index if not exists idx_egm_fsa_session_user
  on egm4000.fsa_session_links(user_id, linked_at desc);

alter table egm4000.fsa_subject_links enable row level security;
alter table egm4000.fsa_session_links enable row level security;

drop policy if exists egm_fsa_subject_links_backend_only on egm4000.fsa_subject_links;
create policy egm_fsa_subject_links_backend_only
  on egm4000.fsa_subject_links
  as restrictive
  for all
  to public
  using (false)
  with check (false);

drop policy if exists egm_fsa_session_links_backend_only on egm4000.fsa_session_links;
create policy egm_fsa_session_links_backend_only
  on egm4000.fsa_session_links
  as restrictive
  for all
  to public
  using (false)
  with check (false);

do $roles$
begin
  if exists (select 1 from pg_roles where rolname='anon') then
    execute 'revoke all on egm4000.fsa_subject_links, egm4000.fsa_session_links from anon';
  end if;
  if exists (select 1 from pg_roles where rolname='authenticated') then
    execute 'revoke all on egm4000.fsa_subject_links, egm4000.fsa_session_links from authenticated';
  end if;
  if exists (select 1 from pg_roles where rolname='service_role') then
    execute 'grant select on egm4000.fsa_subject_links, egm4000.fsa_session_links to service_role';
  end if;
end
$roles$;

create or replace function egm4000.fsa_player_key(p_player_id uuid)
returns text
language sql
immutable
strict
set search_path = pg_catalog, extensions
as $$
  select encode(extensions.digest(p_player_id::text || ':fsa-egm4000-v1', 'sha256'), 'hex')
$$;

revoke all on function egm4000.fsa_player_key(uuid) from public;

create or replace function egm4000.egm_ensure_fsa_session(p_session_id uuid)
returns bigint
language plpgsql
security definer
set search_path = pg_catalog, public, egm4000, extensions
as $$
declare
  s record;
  v_player_key text;
  v_gameplay_session_id bigint;
  v_duration integer;
begin
  select
    ts.id,
    ts.player_id,
    ts.started_at,
    ts.ended_at,
    u.id as user_id
  into s
  from public.fsa_telemetry_sessions ts
  join public.fsa_players fp on fp.id = ts.player_id
  join egm4000.users u
    on u.auth_user_id = fp.auth_user_id
   and u.status = 'active'
  where ts.id = p_session_id;

  if not found then
    return null;
  end if;

  v_player_key := egm4000.fsa_player_key(s.player_id);

  insert into egm4000.fsa_subject_links(player_key, user_id, link_source, last_seen_at)
  values(v_player_key, s.user_id, 'shared_auth_user_id', now())
  on conflict (player_key) do update
    set user_id = excluded.user_id,
        last_seen_at = excluded.last_seen_at;

  perform pg_advisory_xact_lock(hashtextextended(p_session_id::text, 0));

  select gameplay_session_id
  into v_gameplay_session_id
  from egm4000.fsa_session_links
  where fsa_session_id = p_session_id;

  if s.ended_at is not null then
    v_duration := greatest(0, ceil(extract(epoch from (s.ended_at - s.started_at)) / 60.0)::integer);
  else
    v_duration := null;
  end if;

  if v_gameplay_session_id is null then
    insert into egm4000.gameplay_sessions(
      user_id, platform, started_at, ended_at, duration_min,
      starting_bankroll, spend, payout, shots, hits, notes, source
    ) values (
      s.user_id, 'fsa', s.started_at, s.ended_at, v_duration,
      null, null, null, 0, 0,
      'Owned F.S.A. exact telemetry; virtual/non-cash evidence.',
      'fsa-supabase-v2'
    )
    returning id into v_gameplay_session_id;

    insert into egm4000.fsa_session_links(
      fsa_session_id, player_key, user_id, gameplay_session_id
    ) values (
      p_session_id, v_player_key, s.user_id, v_gameplay_session_id
    );
  else
    update egm4000.gameplay_sessions
    set ended_at = coalesce(s.ended_at, ended_at),
        duration_min = coalesce(v_duration, duration_min),
        source = 'fsa-supabase-v2'
    where id = v_gameplay_session_id
      and user_id = s.user_id;
  end if;

  return v_gameplay_session_id;
end
$$;

revoke all on function egm4000.egm_ensure_fsa_session(uuid) from public;

create or replace function egm4000.egm_import_fsa_event(p_event_id bigint)
returns boolean
language plpgsql
security definer
set search_path = pg_catalog, public, egm4000, extensions
as $$
declare
  e record;
  v_gameplay_session_id bigint;
  v_user_id bigint;
  v_player_key text;
  v_event_type text;
  v_shots integer;
  v_hits integer;
  v_row_count integer := 0;
begin
  select * into e
  from public.fsa_telemetry_events
  where id = p_event_id;

  if not found then
    return false;
  end if;

  v_gameplay_session_id := egm4000.egm_ensure_fsa_session(e.session_id);
  if v_gameplay_session_id is null then
    return false;
  end if;

  select user_id, player_key
  into v_user_id, v_player_key
  from egm4000.fsa_session_links
  where fsa_session_id = e.session_id;

  v_event_type := case e.event_type
    when 'session_start' then 'session_started'
    when 'session_end' then 'session_ended'
    when 'power_used' then 'powerup_used'
    else e.event_type
  end;

  insert into egm4000.normalized_events(
    live_session_id,
    user_id,
    source_event_id,
    event_time,
    platform,
    event_type,
    source,
    evidence_type,
    confidence,
    payload
  ) values (
    v_gameplay_session_id,
    v_user_id,
    'fsa-supabase:' || e.id::text,
    e.occurred_at,
    'fsa',
    v_event_type,
    'fsa-supabase-v2',
    'exact_telemetry',
    1,
    coalesce(e.payload, '{}'::jsonb) || jsonb_strip_nulls(jsonb_build_object(
      'fsaSessionId', e.session_id::text,
      'fsaPlayerKey', v_player_key,
      'gameId', e.game_id,
      'room', e.room,
      'producerSource', e.source,
      'currencyBoundary', 'virtual_non_cash'
    ))
  )
  on conflict (source_event_id) where source_event_id is not null do update
    set live_session_id = excluded.live_session_id,
        user_id = excluded.user_id,
        event_time = excluded.event_time,
        platform = excluded.platform,
        event_type = excluded.event_type,
        source = excluded.source,
        evidence_type = excluded.evidence_type,
        confidence = excluded.confidence,
        payload = excluded.payload;

  get diagnostics v_row_count = row_count;

  if e.event_type in ('performance_sample','game_close','session_end') then
    v_shots := case
      when coalesce(e.payload->>'shots','') ~ '^[0-9]{1,8}$' then (e.payload->>'shots')::integer
      else null
    end;
    v_hits := case
      when coalesce(e.payload->>'hits','') ~ '^[0-9]{1,8}$' then (e.payload->>'hits')::integer
      else null
    end;

    update egm4000.gameplay_sessions
    set shots = greatest(shots, coalesce(v_shots, shots)),
        hits = greatest(hits, coalesce(v_hits, hits))
    where id = v_gameplay_session_id
      and user_id = v_user_id;
  end if;

  if e.event_type = 'session_end' then
    update egm4000.gameplay_sessions gs
    set ended_at = coalesce(ts.ended_at, e.occurred_at, gs.ended_at),
        duration_min = greatest(
          0,
          ceil(extract(epoch from (coalesce(ts.ended_at, e.occurred_at) - gs.started_at)) / 60.0)::integer
        )
    from public.fsa_telemetry_sessions ts
    where gs.id = v_gameplay_session_id
      and ts.id = e.session_id;
  end if;

  return v_row_count > 0;
end
$$;

revoke all on function egm4000.egm_import_fsa_event(bigint) from public;

create or replace function egm4000.egm_fsa_event_after_insert()
returns trigger
language plpgsql
security definer
set search_path = pg_catalog, public, egm4000, extensions
as $$
begin
  perform egm4000.egm_import_fsa_event(new.id);
  return new;
end
$$;

revoke all on function egm4000.egm_fsa_event_after_insert() from public;

drop trigger if exists egm_fsa_event_auto_import on public.fsa_telemetry_events;
create trigger egm_fsa_event_auto_import
after insert on public.fsa_telemetry_events
for each row
execute function egm4000.egm_fsa_event_after_insert();

create or replace function public.egm_rpc_import_fsa_telemetry(p_limit integer default 200)
returns jsonb
language plpgsql
security definer
set search_path = pg_catalog, public, egm4000, extensions
as $$
declare
  batch_limit integer := least(greatest(coalesce(p_limit, 200), 1), 1000);
  r record;
  processed_count integer := 0;
  remaining_linked_count bigint := 0;
  unlinked_count bigint := 0;
begin
  for r in
    select e.id
    from public.fsa_telemetry_events e
    join public.fsa_players fp on fp.id = e.player_id
    join egm4000.users u
      on u.auth_user_id = fp.auth_user_id
     and u.status = 'active'
    left join egm4000.normalized_events n
      on n.source_event_id = 'fsa-supabase:' || e.id::text
    where n.id is null
       or n.live_session_id is null
       or n.source <> 'fsa-supabase-v2'
    order by e.id asc
    limit batch_limit
  loop
    perform egm4000.egm_import_fsa_event(r.id);
    processed_count := processed_count + 1;
  end loop;

  select count(*) into remaining_linked_count
  from public.fsa_telemetry_events e
  join public.fsa_players fp on fp.id = e.player_id
  join egm4000.users u
    on u.auth_user_id = fp.auth_user_id
   and u.status = 'active'
  left join egm4000.normalized_events n
    on n.source_event_id = 'fsa-supabase:' || e.id::text
  where n.id is null
     or n.live_session_id is null
     or n.source <> 'fsa-supabase-v2';

  select count(*) into unlinked_count
  from public.fsa_telemetry_events e
  join public.fsa_players fp on fp.id = e.player_id
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
    'schema', 'egm.fsa-supabase-import.v2',
    'processed', processed_count,
    'remainingLinked', remaining_linked_count,
    'pendingUnlinked', unlinked_count,
    'batchLimit', batch_limit,
    'identityRule', 'shared_auth_user_id_to_durable_pseudonymous_subject_link',
    'sessionRule', 'fsa_session_to_egm_gameplay_session',
    'idempotencyRule', 'fsa-supabase:<event_id>',
    'financialRule', 'bankroll_spend_payout_remain_null_virtual_non_cash'
  );
end
$$;

revoke all on function public.egm_rpc_import_fsa_telemetry(integer) from public;

do $grants$
begin
  if exists (select 1 from pg_roles where rolname='anon') then
    execute 'revoke all on function public.egm_rpc_import_fsa_telemetry(integer) from anon';
  end if;
  if exists (select 1 from pg_roles where rolname='authenticated') then
    execute 'revoke all on function public.egm_rpc_import_fsa_telemetry(integer) from authenticated';
  end if;
  if exists (select 1 from pg_roles where rolname='service_role') then
    execute 'grant execute on function public.egm_rpc_import_fsa_telemetry(integer) to service_role';
  end if;
end
$grants$;
