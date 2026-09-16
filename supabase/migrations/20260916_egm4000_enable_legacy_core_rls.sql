-- Defense-in-depth RLS for the legacy/private EGM4000 schema.
-- These tables are backend-only today: anon/authenticated have no direct CRUD grants.
-- Keep FORCE ROW LEVEL SECURITY disabled so trusted owner/SECURITY DEFINER backend paths continue to work.

do $rls$
declare
  t text;
begin
  foreach t in array array[
    'users','tokens','gameplay_sessions','tips','normalized_events',
    'forum_threads','forum_replies','blog_posts','blog_comments','reports',
    'surveys','survey_questions','survey_responses','survey_answers','audit_events'
  ]
  loop
    execute format('alter table egm4000.%I enable row level security', t);

    -- Preserve the existing backend-only grant boundary explicitly.
    execute format('revoke all on table egm4000.%I from anon, authenticated', t);

    -- Defense in depth: even if a browser-role grant is added later by mistake,
    -- this restrictive policy keeps ordinary Data API roles denied.
    execute format(
      'drop policy if exists %I on egm4000.%I',
      'egm_' || t || '_browser_deny_all',
      t
    );
    execute format(
      'create policy %I on egm4000.%I as restrictive for all to anon, authenticated using (false) with check (false)',
      'egm_' || t || '_browser_deny_all',
      t
    );
  end loop;
end
$rls$;
