"""C008 provider-independent commercial access controls.

Implements two monetization capabilities that do not require a payment processor:
A080 first-party affiliate attribution and A084 manually provisioned API access
plans. Payment collection remains outside this module until a real provider is
configured.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
import secrets

from storage import scalar, rowsdict

AFFILIATE_CODE_RE = re.compile(r"[^A-Z0-9_-]+")
API_PLANS = {
    "developer": 100,
    "pro": 1000,
    "enterprise": 10000,
}
API_SCOPES = {"summary", "evidence"}


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _text(value, limit=200):
    return str(value or "").replace("\x00", "").strip()[:limit]


def _json_list(raw):
    try:
        value = json.loads(raw or "[]")
        return value if isinstance(value, list) else []
    except Exception:
        return []


def migrate_commercial_access(con):
    statements = [
        """CREATE TABLE IF NOT EXISTS affiliate_partners(
            id TEXT PRIMARY KEY,
            code TEXT UNIQUE NOT NULL,
            label TEXT NOT NULL,
            landing_path TEXT NOT NULL DEFAULT '/',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS affiliate_attributions(
            user_id INTEGER PRIMARY KEY,
            partner_id TEXT NOT NULL,
            code TEXT NOT NULL,
            attributed_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS affiliate_events(
            event_id TEXT PRIMARY KEY,
            partner_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            user_id INTEGER,
            created_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS api_access_clients(
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            plan TEXT NOT NULL,
            key_hash TEXT UNIQUE NOT NULL,
            key_prefix TEXT NOT NULL,
            scopes_json TEXT NOT NULL DEFAULT '[]',
            daily_quota INTEGER NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_used_at TEXT NOT NULL DEFAULT ''
        )""",
        """CREATE TABLE IF NOT EXISTS api_access_events(
            event_id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL,
            scope TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_affiliate_events_partner ON affiliate_events(partner_id,created_at)",
        "CREATE INDEX IF NOT EXISTS idx_api_access_events_client ON api_access_events(client_id,created_at)",
    ]
    for statement in statements:
        con.execute(statement)
    con.commit()


def normalize_affiliate_code(value):
    code = AFFILIATE_CODE_RE.sub("-", _text(value, 48).upper()).strip("-_")[:40]
    if len(code) < 3:
        raise ValueError("affiliate_code_too_short")
    return code


def validate_landing_path(value):
    path = _text(value or "/", 240)
    if not path.startswith("/") or path.startswith("//") or "\r" in path or "\n" in path:
        raise ValueError("invalid_same_origin_landing_path")
    if path.startswith("/api/") or path.startswith("/go/") or path.startswith("/ref/"):
        raise ValueError("reserved_landing_path")
    return path


def save_affiliate(con, payload):
    if not isinstance(payload, dict):
        raise ValueError("invalid_affiliate_payload")
    partner_id = _text(payload.get("id"), 80) or f"af_{secrets.token_hex(12)}"
    label = _text(payload.get("label"), 140)
    if not label:
        raise ValueError("affiliate_label_required")
    code = normalize_affiliate_code(payload.get("code") or label)
    landing_path = validate_landing_path(payload.get("landing_path") or "/")
    active = 1 if bool(payload.get("active", True)) else 0
    existing = con.execute("SELECT id,created_at FROM affiliate_partners WHERE id=?", (partner_id,)).fetchone()
    duplicate = con.execute("SELECT id FROM affiliate_partners WHERE code=?", (code,)).fetchone()
    if duplicate and str(duplicate["id"]) != partner_id:
        raise ValueError("affiliate_code_exists")
    stamp = _now()
    if existing:
        con.execute(
            "UPDATE affiliate_partners SET code=?,label=?,landing_path=?,active=?,updated_at=? WHERE id=?",
            (code, label, landing_path, active, stamp, partner_id),
        )
    else:
        con.execute(
            "INSERT INTO affiliate_partners(id,code,label,landing_path,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
            (partner_id, code, label, landing_path, active, stamp, stamp),
        )
    con.commit()
    return get_affiliate(con, partner_id)


def archive_affiliate(con, partner_id):
    partner_id = _text(partner_id, 80)
    row = con.execute("SELECT id FROM affiliate_partners WHERE id=?", (partner_id,)).fetchone()
    if not row:
        raise ValueError("affiliate_not_found")
    con.execute("UPDATE affiliate_partners SET active=0,updated_at=? WHERE id=?", (_now(), partner_id))
    con.commit()
    return get_affiliate(con, partner_id)


def get_affiliate(con, partner_id):
    row = con.execute("SELECT * FROM affiliate_partners WHERE id=?", (_text(partner_id, 80),)).fetchone()
    if not row:
        return None
    clicks = int(scalar(con, "SELECT COUNT(*) FROM affiliate_events WHERE partner_id=? AND event_type='click'", (row["id"],)) or 0)
    signups = int(scalar(con, "SELECT COUNT(*) FROM affiliate_attributions WHERE partner_id=?", (row["id"],)) or 0)
    return {
        "id": row["id"],
        "code": row["code"],
        "label": row["label"],
        "landingPath": row["landing_path"],
        "active": bool(row["active"]),
        "clicks": clicks,
        "signups": signups,
        "conversionRate": round(signups / clicks, 4) if clicks else None,
        "referralPath": f"/ref/{row['code']}",
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def admin_affiliates(con):
    rows = con.execute("SELECT id FROM affiliate_partners ORDER BY updated_at DESC,label ASC").fetchall()
    return {
        "schema": "egm.admin.affiliates.v1",
        "partners": [get_affiliate(con, row["id"]) for row in rows],
        "privacy": "Affiliate click events store no raw IP address, browser fingerprint, or visitor identifier. Signup attribution links only an internal registered user to the referral partner that preceded registration.",
    }


def resolve_affiliate_click(con, code):
    try:
        code = normalize_affiliate_code(code)
    except ValueError:
        return None
    row = con.execute("SELECT * FROM affiliate_partners WHERE code=? AND active=1", (code,)).fetchone()
    if not row:
        return None
    con.execute(
        "INSERT INTO affiliate_events(event_id,partner_id,event_type,user_id,created_at) VALUES(?,?,?,?,?)",
        (f"ae_{secrets.token_hex(12)}", row["id"], "click", None, _now()),
    )
    con.commit()
    return {"id": row["id"], "code": row["code"], "landingPath": row["landing_path"]}


def record_affiliate_signup(con, code, user_id):
    if not code or not user_id:
        return False
    try:
        code = normalize_affiliate_code(code)
    except ValueError:
        return False
    partner = con.execute("SELECT id,code FROM affiliate_partners WHERE code=? AND active=1", (code,)).fetchone()
    if not partner:
        return False
    existing = con.execute("SELECT user_id FROM affiliate_attributions WHERE user_id=?", (user_id,)).fetchone()
    if existing:
        return False
    stamp = _now()
    con.execute(
        "INSERT INTO affiliate_attributions(user_id,partner_id,code,attributed_at) VALUES(?,?,?,?)",
        (user_id, partner["id"], partner["code"], stamp),
    )
    con.execute(
        "INSERT INTO affiliate_events(event_id,partner_id,event_type,user_id,created_at) VALUES(?,?,?,?,?)",
        (f"ae_{secrets.token_hex(12)}", partner["id"], "signup", user_id, stamp),
    )
    return True


def _normalize_scopes(value):
    if isinstance(value, str):
        value = [x.strip() for x in value.split(",") if x.strip()]
    if not isinstance(value, list):
        value = []
    scopes = []
    for raw in value:
        scope = _text(raw, 40).lower()
        if scope in API_SCOPES and scope not in scopes:
            scopes.append(scope)
    if not scopes:
        raise ValueError("api_scope_required")
    return scopes


def _api_secret():
    return "egm_api_" + secrets.token_urlsafe(32)


def _hash_key(raw):
    return hashlib.sha256(str(raw).encode()).hexdigest()


def _client_dict(con, row):
    day = _today()
    used = int(scalar(con, "SELECT COUNT(*) FROM api_access_events WHERE client_id=? AND created_at LIKE ?", (row["id"], day + "%")) or 0)
    quota = max(1, int(row["daily_quota"] or 1))
    return {
        "id": row["id"],
        "name": row["name"],
        "plan": row["plan"],
        "keyPrefix": row["key_prefix"],
        "scopes": _json_list(row["scopes_json"]),
        "dailyQuota": quota,
        "usedToday": used,
        "remainingToday": max(0, quota - used),
        "active": bool(row["active"]),
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
        "lastUsedAt": row["last_used_at"] or "",
    }


def save_api_client(con, payload):
    if not isinstance(payload, dict):
        raise ValueError("invalid_api_client_payload")
    client_id = _text(payload.get("id"), 80) or f"ac_{secrets.token_hex(12)}"
    name = _text(payload.get("name"), 160)
    if not name:
        raise ValueError("api_client_name_required")
    plan = _text(payload.get("plan") or "developer", 30).lower()
    if plan not in API_PLANS:
        raise ValueError("invalid_api_plan")
    scopes = _normalize_scopes(payload.get("scopes"))
    try:
        quota = int(payload.get("daily_quota") or API_PLANS[plan])
    except Exception:
        raise ValueError("invalid_daily_quota")
    quota = max(1, min(100000, quota))
    active = 1 if bool(payload.get("active", True)) else 0
    row = con.execute("SELECT * FROM api_access_clients WHERE id=?", (client_id,)).fetchone()
    stamp = _now()
    raw_key = None
    if row:
        con.execute(
            "UPDATE api_access_clients SET name=?,plan=?,scopes_json=?,daily_quota=?,active=?,updated_at=? WHERE id=?",
            (name, plan, json.dumps(scopes), quota, active, stamp, client_id),
        )
    else:
        raw_key = _api_secret()
        con.execute(
            """INSERT INTO api_access_clients(
                 id,name,plan,key_hash,key_prefix,scopes_json,daily_quota,active,created_at,updated_at,last_used_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (client_id, name, plan, _hash_key(raw_key), raw_key[:16], json.dumps(scopes), quota, active, stamp, stamp, ""),
        )
    con.commit()
    current = con.execute("SELECT * FROM api_access_clients WHERE id=?", (client_id,)).fetchone()
    out = _client_dict(con, current)
    if raw_key:
        out["apiKey"] = raw_key
        out["apiKeyNotice"] = "Shown once. Store it securely; EGM4000 keeps only a SHA-256 hash."
    return out


def rotate_api_client_key(con, client_id):
    client_id = _text(client_id, 80)
    row = con.execute("SELECT * FROM api_access_clients WHERE id=?", (client_id,)).fetchone()
    if not row:
        raise ValueError("api_client_not_found")
    raw_key = _api_secret()
    con.execute(
        "UPDATE api_access_clients SET key_hash=?,key_prefix=?,updated_at=? WHERE id=?",
        (_hash_key(raw_key), raw_key[:16], _now(), client_id),
    )
    con.commit()
    current = con.execute("SELECT * FROM api_access_clients WHERE id=?", (client_id,)).fetchone()
    out = _client_dict(con, current)
    out["apiKey"] = raw_key
    out["apiKeyNotice"] = "Rotated key shown once. The previous key is invalid immediately."
    return out


def archive_api_client(con, client_id):
    client_id = _text(client_id, 80)
    row = con.execute("SELECT id FROM api_access_clients WHERE id=?", (client_id,)).fetchone()
    if not row:
        raise ValueError("api_client_not_found")
    con.execute("UPDATE api_access_clients SET active=0,updated_at=? WHERE id=?", (_now(), client_id))
    con.commit()
    row = con.execute("SELECT * FROM api_access_clients WHERE id=?", (client_id,)).fetchone()
    return _client_dict(con, row)


def admin_api_clients(con):
    rows = con.execute("SELECT * FROM api_access_clients ORDER BY updated_at DESC,name ASC").fetchall()
    return {
        "schema": "egm.admin.api-access.v1",
        "clients": [_client_dict(con, row) for row in rows],
        "plans": [{"id": key, "defaultDailyQuota": value} for key, value in API_PLANS.items()],
        "availableScopes": sorted(API_SCOPES),
        "security": "API keys are displayed only when created or rotated. Only SHA-256 key hashes and non-secret prefixes are persisted.",
    }


def authorize_api_client(con, raw_key, required_scope):
    raw_key = _text(raw_key, 240)
    if not raw_key.startswith("egm_api_") or len(raw_key) < 32:
        raise ValueError("invalid_api_key")
    row = con.execute("SELECT * FROM api_access_clients WHERE key_hash=? AND active=1", (_hash_key(raw_key),)).fetchone()
    if not row:
        raise ValueError("invalid_api_key")
    scopes = _json_list(row["scopes_json"])
    if required_scope not in scopes:
        raise ValueError("api_scope_denied")
    used = int(scalar(con, "SELECT COUNT(*) FROM api_access_events WHERE client_id=? AND created_at LIKE ?", (row["id"], _today() + "%")) or 0)
    quota = max(1, int(row["daily_quota"] or 1))
    if used >= quota:
        raise ValueError("api_daily_quota_exceeded")
    return row, used, quota


def record_api_usage(con, row, scope, endpoint):
    stamp = _now()
    con.execute(
        "INSERT INTO api_access_events(event_id,client_id,scope,endpoint,created_at) VALUES(?,?,?,?,?)",
        (f"au_{secrets.token_hex(12)}", row["id"], scope, _text(endpoint, 160), stamp),
    )
    con.execute("UPDATE api_access_clients SET last_used_at=?,updated_at=? WHERE id=?", (stamp, stamp, row["id"]))
    con.commit()


def api_platform_summary(con):
    historical = rowsdict(con.execute(
        "SELECT platform,COUNT(*) session_count FROM gameplay_sessions GROUP BY platform ORDER BY session_count DESC,platform ASC"
    ).fetchall())
    live = rowsdict(con.execute(
        "SELECT platform,COUNT(*) session_count FROM live_sessions GROUP BY platform ORDER BY session_count DESC,platform ASC"
    ).fetchall())
    return {
        "schema": "egm.developer.platform-summary.v1",
        "historicalSessions": historical,
        "authorizedLiveSessions": live,
        "privacy": "Aggregate session counts only; no user-level records are returned.",
    }


def api_evidence_summary(con):
    rows = rowsdict(con.execute(
        """SELECT evidence_type,platform,COUNT(*) event_count
           FROM normalized_events
           GROUP BY evidence_type,platform
           ORDER BY event_count DESC,evidence_type ASC,platform ASC"""
    ).fetchall())
    return {
        "schema": "egm.developer.evidence-summary.v1",
        "evidence": rows,
        "boundary": "Counts describe stored authorized evidence. They do not expose credentials, hidden server state, or predictions of random outcomes.",
    }
