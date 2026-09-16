"""C008 A076 premium evidence export/report add-on.

This feature deliberately separates *access provisioning* from payment claims.
Until a billing provider is configured, access can only be granted as
``complimentary`` or ``manual_external_unverified``. The latter means an owner
provisioned access after an external/manual process; EGM4000 does not claim the
payment was provider-verified.

Artifacts contain the authenticated user's own gameplay-session and coaching-tip
records only. Authentication credentials, session tokens, visitor identifiers,
other users' data, and owner audit data are never included.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import secrets
from datetime import datetime, timezone

from storage import rowdict, rowsdict, scalar

FEATURE_ID = "A076"
ALLOWED_SOURCES = {"complimentary", "manual_external_unverified"}
FORMATS = {"json", "csv"}
HISTORICAL_BOUNDARY = (
    "This export summarizes historical evidence only. It does not predict random outcomes, "
    "guarantee winnings, or recommend increasing spend or play time."
)
PAYMENT_BOUNDARY = (
    "Access provisioning is not proof of payment. Until a billing provider is configured, "
    "EGM4000 records only complimentary or manual external/unverified access."
)
MAX_EXPORT_ROWS = 20000


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _text(value, limit=1000):
    return str(value or "").replace("\x00", "").strip()[:limit]


def migrate_export_addon(con):
    con.execute(
        """CREATE TABLE IF NOT EXISTS commercial_entitlements(
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            feature_id TEXT NOT NULL,
            source TEXT NOT NULL,
            status TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            granted_by INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    con.execute(
        """CREATE TABLE IF NOT EXISTS export_artifacts(
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            feature_id TEXT NOT NULL,
            format TEXT NOT NULL,
            filename TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            content_text TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            row_count INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_commercial_entitlement_user_feature ON commercial_entitlements(user_id,feature_id,updated_at)"
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_export_artifacts_user_time ON export_artifacts(user_id,created_at)"
    )
    con.commit()


def _user_exists(con, user_id):
    return bool(scalar(con, "SELECT COUNT(*) FROM users WHERE id=? AND status='active'", (int(user_id),)) or 0)


def entitlement_for_user(con, user_id):
    row = con.execute(
        "SELECT * FROM commercial_entitlements WHERE user_id=? AND feature_id=? ORDER BY updated_at DESC LIMIT 1",
        (int(user_id), FEATURE_ID),
    ).fetchone()
    if not row:
        return {
            "featureId": FEATURE_ID,
            "userId": int(user_id),
            "active": False,
            "status": "not_granted",
            "source": None,
            "note": "",
            "updatedAt": None,
            "paymentBoundary": PAYMENT_BOUNDARY,
        }
    row = rowdict(row)
    return {
        "id": row["id"],
        "featureId": row["feature_id"],
        "userId": int(row["user_id"]),
        "active": row["status"] == "active",
        "status": row["status"],
        "source": row["source"],
        "note": row["note"],
        "grantedBy": row["granted_by"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
        "paymentBoundary": PAYMENT_BOUNDARY,
    }


def grant_entitlement(con, user_id, source, note, granted_by):
    user_id = int(user_id)
    granted_by = int(granted_by) if granted_by is not None else None
    source = _text(source, 80)
    note = _text(note, 2000)
    if source not in ALLOWED_SOURCES:
        raise ValueError("unsupported_entitlement_source")
    if not _user_exists(con, user_id):
        raise ValueError("entitlement_user_not_found")
    stamp = _now()
    existing = con.execute(
        "SELECT id FROM commercial_entitlements WHERE user_id=? AND feature_id=? ORDER BY updated_at DESC LIMIT 1",
        (user_id, FEATURE_ID),
    ).fetchone()
    if existing:
        entitlement_id = existing["id"]
        con.execute(
            "UPDATE commercial_entitlements SET source=?,status='active',note=?,granted_by=?,updated_at=? WHERE id=?",
            (source, note, granted_by, stamp, entitlement_id),
        )
    else:
        entitlement_id = f"ce_{secrets.token_hex(12)}"
        con.execute(
            "INSERT INTO commercial_entitlements(id,user_id,feature_id,source,status,note,granted_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (entitlement_id, user_id, FEATURE_ID, source, "active", note, granted_by, stamp, stamp),
        )
    con.commit()
    return entitlement_for_user(con, user_id)


def revoke_entitlement(con, user_id, note, granted_by):
    user_id = int(user_id)
    existing = con.execute(
        "SELECT id FROM commercial_entitlements WHERE user_id=? AND feature_id=? ORDER BY updated_at DESC LIMIT 1",
        (user_id, FEATURE_ID),
    ).fetchone()
    if not existing:
        raise ValueError("entitlement_not_found")
    stamp = _now()
    con.execute(
        "UPDATE commercial_entitlements SET status='revoked',note=?,granted_by=?,updated_at=? WHERE id=?",
        (_text(note, 2000), int(granted_by) if granted_by is not None else None, stamp, existing["id"]),
    )
    con.commit()
    return entitlement_for_user(con, user_id)


def _artifact_dict(row, include_content=False):
    row = rowdict(row)
    out = {
        "id": row["id"],
        "featureId": row["feature_id"],
        "format": row["format"],
        "filename": row["filename"],
        "mimeType": row["mime_type"],
        "sha256": row["sha256"],
        "rowCount": int(row["row_count"]),
        "createdAt": row["created_at"],
        "historicalBoundary": HISTORICAL_BOUNDARY,
    }
    if include_content:
        out["content"] = row["content_text"]
    return out


def list_artifacts(con, user_id):
    rows = con.execute(
        "SELECT * FROM export_artifacts WHERE user_id=? AND feature_id=? ORDER BY created_at DESC LIMIT 50",
        (int(user_id), FEATURE_ID),
    ).fetchall()
    return [_artifact_dict(row) for row in rows]


def get_artifact(con, user_id, artifact_id):
    artifact_id = _text(artifact_id, 120)
    row = con.execute(
        "SELECT * FROM export_artifacts WHERE id=? AND user_id=? AND feature_id=?",
        (artifact_id, int(user_id), FEATURE_ID),
    ).fetchone()
    if not row:
        raise ValueError("export_artifact_not_found")
    return _artifact_dict(row, include_content=True)


def _load_owned_data(con, user_id):
    sessions = rowsdict(
        con.execute(
            "SELECT id,platform,started_at,duration_min,starting_bankroll,spend,payout,shots,hits,notes,source FROM gameplay_sessions WHERE user_id=? ORDER BY started_at ASC,id ASC",
            (int(user_id),),
        ).fetchall()
    )
    tips = rowsdict(
        con.execute(
            "SELECT id,session_id,created_at,title,body,evidence,confidence FROM tips WHERE user_id=? ORDER BY created_at ASC,id ASC",
            (int(user_id),),
        ).fetchall()
    )
    total = len(sessions) + len(tips)
    if total > MAX_EXPORT_ROWS:
        raise ValueError("export_too_large_for_inline_artifact")
    return sessions, tips


def _summary(sessions, tips):
    shots = sum(int(x.get("shots") or 0) for x in sessions)
    hits = sum(int(x.get("hits") or 0) for x in sessions)
    minutes = sum(int(x.get("duration_min") or 0) for x in sessions)
    spend = round(sum(float(x.get("spend") or 0) for x in sessions), 2)
    payout = round(sum(float(x.get("payout") or 0) for x in sessions), 2)
    return {
        "sessionCount": len(sessions),
        "tipCount": len(tips),
        "totalMinutes": minutes,
        "totalShots": shots,
        "totalHits": hits,
        "historicalHitRate": round(hits / shots, 6) if shots else None,
        "historicalSpend": spend,
        "historicalPayout": payout,
    }


def _json_content(user_id, stamp, sessions, tips):
    payload = {
        "schema": "egm.a076.evidence-export.v1",
        "featureId": FEATURE_ID,
        "userId": int(user_id),
        "generatedAt": stamp,
        "historicalBoundary": HISTORICAL_BOUNDARY,
        "summary": _summary(sessions, tips),
        "sessions": sessions,
        "tips": tips,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False), "application/json"


def _csv_content(user_id, stamp, sessions, tips):
    fieldnames = [
        "record_type", "record_id", "user_id", "session_id", "platform", "timestamp",
        "duration_min", "starting_bankroll", "spend", "payout", "shots", "hits",
        "title", "body", "evidence", "confidence", "notes", "source",
    ]
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=fieldnames)
    writer.writeheader()
    for row in sessions:
        writer.writerow({
            "record_type": "gameplay_session", "record_id": row["id"], "user_id": int(user_id),
            "session_id": row["id"], "platform": row["platform"], "timestamp": row["started_at"],
            "duration_min": row["duration_min"], "starting_bankroll": row["starting_bankroll"],
            "spend": row["spend"], "payout": row["payout"], "shots": row["shots"],
            "hits": row["hits"], "notes": row["notes"], "source": row["source"],
        })
    for row in tips:
        writer.writerow({
            "record_type": "coaching_tip", "record_id": row["id"], "user_id": int(user_id),
            "session_id": row["session_id"], "timestamp": row["created_at"], "title": row["title"],
            "body": row["body"], "evidence": row["evidence"], "confidence": row["confidence"],
        })
    out.write(f"# generated_at,{stamp}\n# boundary,{HISTORICAL_BOUNDARY}\n")
    return out.getvalue(), "text/csv"


def generate_artifact(con, user_id, fmt):
    user_id = int(user_id)
    fmt = _text(fmt, 20).lower()
    if fmt not in FORMATS:
        raise ValueError("unsupported_export_format")
    entitlement = entitlement_for_user(con, user_id)
    if not entitlement["active"]:
        raise ValueError("export_addon_entitlement_required")
    sessions, tips = _load_owned_data(con, user_id)
    stamp = _now()
    if fmt == "json":
        content, mime = _json_content(user_id, stamp, sessions, tips)
    else:
        content, mime = _csv_content(user_id, stamp, sessions, tips)
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    artifact_id = f"ex_{secrets.token_hex(12)}"
    compact_stamp = stamp.replace(":", "").replace("-", "").replace("+00:00", "Z")
    filename = f"egm4000-evidence-{user_id}-{compact_stamp}.{fmt}"
    con.execute(
        "INSERT INTO export_artifacts(id,user_id,feature_id,format,filename,mime_type,content_text,sha256,row_count,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (artifact_id, user_id, FEATURE_ID, fmt, filename, mime, content, digest, len(sessions) + len(tips), stamp),
    )
    con.commit()
    row = con.execute("SELECT * FROM export_artifacts WHERE id=?", (artifact_id,)).fetchone()
    return _artifact_dict(row, include_content=True)


def user_export_status(con, user_id):
    return {
        "schema": "egm.a076.export-addon.v1",
        "featureId": FEATURE_ID,
        "entitlement": entitlement_for_user(con, user_id),
        "artifacts": list_artifacts(con, user_id),
        "formats": sorted(FORMATS),
        "historicalBoundary": HISTORICAL_BOUNDARY,
        "paymentBoundary": PAYMENT_BOUNDARY,
    }


def admin_export_status(con):
    rows = con.execute(
        """SELECT e.*,u.username,u.display_name
           FROM commercial_entitlements e
           JOIN users u ON u.id=e.user_id
           WHERE e.feature_id=?
           ORDER BY e.updated_at DESC""",
        (FEATURE_ID,),
    ).fetchall()
    entitlements = []
    for row in rows:
        d = rowdict(row)
        entitlements.append({
            "id": d["id"], "userId": int(d["user_id"]), "username": d["username"],
            "displayName": d["display_name"], "source": d["source"], "status": d["status"],
            "note": d["note"], "grantedBy": d["granted_by"], "createdAt": d["created_at"],
            "updatedAt": d["updated_at"],
        })
    artifact_count = int(scalar(con, "SELECT COUNT(*) FROM export_artifacts WHERE feature_id=?", (FEATURE_ID,)) or 0)
    return {
        "schema": "egm.admin.a076.export-addon.v1",
        "featureId": FEATURE_ID,
        "entitlements": entitlements,
        "artifactCount": artifact_count,
        "allowedSources": sorted(ALLOWED_SOURCES),
        "paymentBoundary": PAYMENT_BOUNDARY,
        "historicalBoundary": HISTORICAL_BOUNDARY,
    }
