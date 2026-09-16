\set ON_ERROR_STOP on

insert into egm4000.users(id,username,email,password_hash,display_name,status,is_synthetic,auth_user_id)
values (9001,'bridge_test','bridge-test@example.invalid','not-a-login-hash','Bridge Test','active',true,'11111111-1111-4111-8111-111111111111');

insert into public.fsa_players(id,auth_user_id)
values ('22222222-2222-4222-8222-222222222222','11111111-1111-4111-8111-111111111111');

insert into public.fsa_telemetry_sessions(
  id,player_id,client_kind,build,low_data,started_at,last_event_at,ended_at,event_count,last_game_id,last_room
) values (
  '33333333-3333-4333-8333-333333333333',
  '22222222-2222-4222-8222-222222222222',
  'web','ci-bridge-v2',false,now()-interval '2 minutes',now(),now(),3,'reef-run',1
);

insert into public.fsa_telemetry_events(session_id,player_id,event_type,game_id,room,payload,source,occurred_at)
values
('33333333-3333-4333-8333-333333333333','22222222-2222-4222-8222-222222222222','session_start','reef-run',1,'{"client":"web","build":"ci-bridge-v2","low_data":false}'::jsonb,'server_observed',now()-interval '2 minutes'),
('33333333-3333-4333-8333-333333333333','22222222-2222-4222-8222-222222222222','performance_sample','reef-run',1,'{"shots":42,"hits":30,"kills":7,"score":1200,"combo":4,"fever":88,"wave":2}'::jsonb,'client_observed',now()-interval '1 minute'),
('33333333-3333-4333-8333-333333333333','22222222-2222-4222-8222-222222222222','session_end','reef-run',1,'{"shots":42,"hits":30,"kills":7,"score":1200,"combo":4,"fever":88,"wave":2,"duration_ms":120000}'::jsonb,'server_observed',now());

-- Re-processing one event must update in place, never duplicate it.
select egm4000.egm_import_fsa_event((select min(id) from public.fsa_telemetry_events));

-- Backfill importer should have nothing left to repair after trigger ingestion.
select public.egm_rpc_import_fsa_telemetry(200);

do $test$
declare
  v_subjects integer;
  v_links integer;
  v_sessions integer;
  v_events integer;
  v_shots integer;
  v_hits integer;
  v_financial_clean boolean;
  v_exact boolean;
  v_grouped boolean;
  v_virtual boolean;
  v_anon_exec boolean;
  v_auth_exec boolean;
  v_service_exec boolean;
  v_rls_subject boolean;
  v_rls_session boolean;
begin
  select count(*) into v_subjects from egm4000.fsa_subject_links;
  select count(*) into v_links from egm4000.fsa_session_links;
  select count(*) into v_sessions from egm4000.gameplay_sessions where source='fsa-supabase-v2';
  select count(*) into v_events from egm4000.normalized_events where source='fsa-supabase-v2';
  select shots,hits,(starting_bankroll is null and spend is null and payout is null)
    into v_shots,v_hits,v_financial_clean
    from egm4000.gameplay_sessions where source='fsa-supabase-v2';
  select bool_and(evidence_type='exact_telemetry' and confidence=1),
         bool_and(live_session_id=(select gameplay_session_id from egm4000.fsa_session_links limit 1)),
         bool_and(payload->>'currencyBoundary'='virtual_non_cash')
    into v_exact,v_grouped,v_virtual
    from egm4000.normalized_events where source='fsa-supabase-v2';

  select has_function_privilege('anon','public.egm_rpc_import_fsa_telemetry(integer)','EXECUTE') into v_anon_exec;
  select has_function_privilege('authenticated','public.egm_rpc_import_fsa_telemetry(integer)','EXECUTE') into v_auth_exec;
  select has_function_privilege('service_role','public.egm_rpc_import_fsa_telemetry(integer)','EXECUTE') into v_service_exec;
  select relrowsecurity into v_rls_subject from pg_class where oid='egm4000.fsa_subject_links'::regclass;
  select relrowsecurity into v_rls_session from pg_class where oid='egm4000.fsa_session_links'::regclass;

  if v_subjects<>1 then raise exception 'expected 1 subject link, got %',v_subjects; end if;
  if v_links<>1 then raise exception 'expected 1 session link, got %',v_links; end if;
  if v_sessions<>1 then raise exception 'expected 1 gameplay session, got %',v_sessions; end if;
  if v_events<>3 then raise exception 'expected exactly 3 normalized events after idempotent replay, got %',v_events; end if;
  if v_shots<>42 or v_hits<>30 then raise exception 'session metrics mismatch shots=% hits=%',v_shots,v_hits; end if;
  if not v_financial_clean then raise exception 'financial fields must remain NULL'; end if;
  if not v_exact then raise exception 'exact telemetry evidence contract failed'; end if;
  if not v_grouped then raise exception 'normalized events are not grouped under the linked gameplay session'; end if;
  if not v_virtual then raise exception 'virtual/non-cash boundary missing from normalized payload'; end if;
  if v_anon_exec or v_auth_exec or not v_service_exec then raise exception 'import RPC grants are wrong anon=% auth=% service=%',v_anon_exec,v_auth_exec,v_service_exec; end if;
  if not v_rls_subject or not v_rls_session then raise exception 'bridge link tables must have RLS enabled'; end if;

  raise notice 'FSA_EGM4000_SUPABASE_CONSUMER_V2=PASS subjects=% sessions=% events=% shots=% hits=%',v_subjects,v_sessions,v_events,v_shots,v_hits;
end
$test$;
