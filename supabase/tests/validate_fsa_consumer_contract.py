#!/usr/bin/env python3
"""Static guardrails for the F.S.A. -> EGM4000 Supabase consumer migration.

This is intentionally a repository contract check, not a substitute for applying the
migration to a real Postgres/Supabase project and exercising the RPC there.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "supabase" / "migrations" / "20260916_egm_fsa_supabase_consumer_v1.sql"
text = MIGRATION.read_text(encoding="utf-8")

required = {
    "server-only RPC": "public.egm_rpc_import_fsa_telemetry",
    "shared-auth identity link": "u.auth_user_id = fp.auth_user_id",
    "active EGM user boundary": "u.status = 'active'",
    "idempotent source prefix": "'fsa-supabase:' || e.id::text",
    "pseudonymous player key": "'fsaPlayerKey'",
    "owned telemetry evidence label": "'exact_telemetry'",
    "service-role grant": "to service_role",
    "ordinary client revoke": "from public, anon, authenticated",
}

missing = [label for label, needle in required.items() if needle not in text]
if missing:
    raise SystemExit("missing FSA consumer contract guardrails: " + ", ".join(missing))

if "'fsaPlayerId'" in text or '"fsaPlayerId"' in text:
    raise SystemExit("raw F.S.A. player UUID payload key must not be added to EGM normalized events")

if "grant execute on function public.egm_rpc_import_fsa_telemetry(integer)\n  to authenticated" in text:
    raise SystemExit("authenticated clients must not receive execute permission on the importer")

print("F.S.A. -> EGM4000 Supabase consumer contract guardrails verified.")
