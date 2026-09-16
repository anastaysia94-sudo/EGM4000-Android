"""C003 production readiness and security policy helpers."""
from __future__ import annotations

import base64
import hashlib
from urllib.parse import urlparse

SCHEMA="egm.production-readiness.v1"


def session_token_hash(raw: str) -> str:
    return hashlib.sha256(str(raw or "").encode("utf-8")).hexdigest()


def _long(env,name,minimum=32):
    return len(str(env.get(name) or "")) >= minimum


def _https(value):
    try:
        p=urlparse(str(value or ""));return p.scheme=="https" and bool(p.netloc)
    except Exception:return False


def _valid_totp(value):
    raw=str(value or "").replace(" ","").upper()
    if len(raw)<16:return False
    try:
        padded=raw+'='*((8-len(raw)%8)%8);return len(base64.b32decode(padded,casefold=True))>=10
    except Exception:return False


def evaluate(env):
    env=dict(env or {});production=str(env.get("EGM_ENV") or "").lower()=="production";checks=[]
    def add(code,ok,required=True,detail=""):
        checks.append({"code":code,"ok":bool(ok),"required":bool(required),"detail":detail})
    add("secure_cookies",env.get("EGM_SECURE_COOKIES")=="1",production,"Secure cookies must be enabled on public HTTPS deployments.")
    add("public_https_url",_https(env.get("EGM_PUBLIC_BASE_URL")),production,"Canonical public base URL must use HTTPS.")
    add("owner_password",_long(env,"EGM_OWNER_PASSWORD",20),production,"Bootstrap/owner secret must be at least 20 characters.")
    add("visitor_hmac_secret",_long(env,"EGM_VISITOR_SECRET",32),production,"Visitor HMAC secret must be independent and at least 32 characters.")
    add("visitor_secret_separate",bool(env.get("EGM_VISITOR_SECRET")) and env.get("EGM_VISITOR_SECRET")!=env.get("EGM_OWNER_PASSWORD"),production,"Visitor HMAC secret must differ from owner password.")
    add("owner_recovery",_long(env,"EGM_OWNER_RECOVERY_TOKEN",32),production,"Owner recovery token must be deployment-held and at least 32 characters.")
    add("owner_totp",_valid_totp(env.get("EGM_OWNER_TOTP_SECRET")),production,"Owner TOTP must be deployment-held and valid Base32.")
    db=str(env.get("DATABASE_URL") or "")
    add("durable_postgres",db.startswith("postgres://") or db.startswith("postgresql://"),production,"Production must use durable PostgreSQL/Supabase-compatible storage.")
    add("trusted_proxy_explicit",env.get("EGM_TRUST_PROXY") in ("0","1"),production,"Proxy trust must be explicit; only trusted deployments should set it to 1.")
    add("backup_policy",bool(env.get("EGM_BACKUP_DIR") or env.get("EGM_MANAGED_DATABASE_BACKUPS") == "1"),production,"Configure durable logical backups or declare managed database backups.")
    if env.get("EGM_BILLING_WEBHOOK_SECRET"):
        add("billing_signing_secret",_long(env,"EGM_BILLING_WEBHOOK_SECRET",32),True,"Billing HMAC secret must be at least 32 characters when enabled.")
    if env.get("EGM_FSA_TELEMETRY_TOKEN"):
        add("fsa_bridge_secret",_long(env,"EGM_FSA_TELEMETRY_TOKEN",32),True,"F.S.A. bridge token must be at least 32 characters when enabled.")
    missing=[x["code"] for x in checks if x["required"] and not x["ok"]]
    return {"schema":SCHEMA,"production":production,"ready":not missing,"missing":missing,"checks":checks}


def require_production_ready(env):
    result=evaluate(env)
    if result["production"] and not result["ready"]:
        raise RuntimeError("production_readiness_failed:"+",".join(result["missing"]))
    return result
