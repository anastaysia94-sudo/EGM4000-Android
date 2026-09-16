-- EGM4000 <- F.S.A. Supabase consumer scheduler v1
-- Runs the server-only importer inside Postgres. No client/service-role secret is stored.

create extension if not exists pg_cron;

-- cron.schedule replaces an existing job with the same name, so this migration is
-- idempotent with respect to the named importer job.
select cron.schedule(
  'egm-fsa-telemetry-import-v1',
  '* * * * *',
  $$select public.egm_rpc_import_fsa_telemetry(1000);$$
);

comment on extension pg_cron is
  'Database-internal scheduler used by EGM4000 for the server-only F.S.A. telemetry import job.';
