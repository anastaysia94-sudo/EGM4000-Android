"""Production security configuration checks for EGM4000.

No secret values are returned from this module. It only reports whether required
controls are configured and blocks production startup when critical controls are
missing.
"""
from __future__ import annotations

import os


def _truthy(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def security_status(env=None):
    env = dict(os.environ if env is None else env)
    mode = str(env.get("EGM_ENV", "development")).strip().lower()
    production = mode in {"production", "prod"}
    secure_cookies = _truthy(env.get("EGM_SECURE_COOKIES"))
    owner_secret = bool(str(env.get("EGM_OWNER_PASSWORD", "")).strip())
    visitor_secret = bool(str(env.get("EGM_VISITOR_SECRET", "")).strip())
    fsa_secret = bool(str(env.get("EGM_FSA_TELEMETRY_TOKEN", "")).strip())
    checks = {
        "productionMode": production,
        "secureCookies": secure_cookies,
        "ownerPasswordConfigured": owner_secret,
        "visitorSecretConfigured": visitor_secret,
        "fsaTelemetryTokenConfigured": fsa_secret,
    }
    critical = {
        "secureCookies": secure_cookies,
        "ownerPasswordConfigured": owner_secret,
        "visitorSecretConfigured": visitor_secret,
    }
    missing = [name for name, ok in critical.items() if production and not ok]
    return {
        "schema": "egm.security-status.v1",
        "mode": mode,
        "readyForProduction": not missing if production else False,
        "checks": checks,
        "missingCritical": missing,
        "note": "This endpoint reports configuration state only. Secret values are never returned.",
    }


def enforce_production_security(env=None):
    status = security_status(env)
    if status["checks"]["productionMode"] and status["missingCritical"]:
        names = ", ".join(status["missingCritical"])
        raise RuntimeError(f"EGM4000 production security configuration incomplete: {names}")
    return status


def security_headers(secure=False):
    headers = {
        "Content-Security-Policy": "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'",
        "X-Frame-Options": "DENY",
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Resource-Policy": "same-origin",
    }
    if secure:
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return headers
