#!/usr/bin/env python3
"""Static guardrails for the database-internal F.S.A. telemetry import schedule."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "supabase" / "migrations" / "20260916_egm_fsa_consumer_scheduler_v1.sql"
text = MIGRATION.read_text(encoding="utf-8")

required = {
    "pg_cron extension": "create extension if not exists pg_cron",
    "stable job name": "egm-fsa-telemetry-import-v1",
    "one-minute schedule": "'* * * * *'",
    "server-side importer call": "select public.egm_rpc_import_fsa_telemetry(1000);",
}

missing = [label for label, needle in required.items() if needle not in text]
if missing:
    raise SystemExit("missing FSA scheduler contract guardrails: " + ", ".join(missing))

for forbidden in ("service_role", "apikey", "authorization", "http_post", "net.http"):
    if forbidden.lower() in text.lower():
        raise SystemExit(f"scheduler migration must remain database-internal; forbidden token: {forbidden}")

print("F.S.A. -> EGM4000 scheduler contract guardrails verified.")
