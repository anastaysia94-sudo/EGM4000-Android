"""C008 A092 optional tip-jar / donation support links.

Support links are voluntary outbound HTTPS links. EGM4000 records aggregate click
counts only and never represents a click as a donation, payment, or entitlement.
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone

from monetization_assets import validate_destination, validate_claims
from storage import scalar

DEFAULT_DISCLOSURE = "Voluntary support link. Clicking does not prove a donation or purchase, and support never changes gameplay evidence or random outcomes."


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _text(value, limit=500):
    return str(value or "").replace("\x00", "").strip()[:limit]


def migrate_support_links(con):
    con.execute(
        """CREATE TABLE IF NOT EXISTS support_links(
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            body TEXT NOT NULL DEFAULT '',
            destination_url TEXT NOT NULL,
            disclosure TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    con.execute(
        """CREATE TABLE IF NOT EXISTS support_link_events(
            event_id TEXT PRIMARY KEY,
            support_link_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_support_link_events_link ON support_link_events(support_link_id,created_at)")
    con.commit()


def _link_dict(con, row, public=False):
    clicks = int(scalar(con, "SELECT COUNT(*) FROM support_link_events WHERE support_link_id=? AND event_type='click'", (row["id"],)) or 0)
    out = {
        "id": row["id"],
        "title": row["title"],
        "body": row["body"],
        "disclosure": row["disclosure"],
        "active": bool(row["active"]),
        "supportPath": f"/support/{row['id']}",
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }
    if public:
        return out
    out["destinationUrl"] = row["destination_url"]
    out["clicks"] = clicks
    return out


def save_support_link(con, payload):
    if not isinstance(payload, dict):
        raise ValueError("invalid_support_link_payload")
    link_id = _text(payload.get("id"), 80) or f"sl_{secrets.token_hex(12)}"
    title = _text(payload.get("title"), 180)
    body = _text(payload.get("body"), 2500)
    if not title:
        raise ValueError("support_link_title_required")
    destination = validate_destination(payload.get("destination_url"))
    disclosure = _text(payload.get("disclosure") or DEFAULT_DISCLOSURE, 500)
    validate_claims(title, body, disclosure)
    active = 1 if bool(payload.get("active")) else 0
    stamp = _now()
    existing = con.execute("SELECT id FROM support_links WHERE id=?", (link_id,)).fetchone()
    if existing:
        con.execute(
            "UPDATE support_links SET title=?,body=?,destination_url=?,disclosure=?,active=?,updated_at=? WHERE id=?",
            (title, body, destination, disclosure, active, stamp, link_id),
        )
    else:
        con.execute(
            "INSERT INTO support_links(id,title,body,destination_url,disclosure,active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
            (link_id, title, body, destination, disclosure, active, stamp, stamp),
        )
    con.commit()
    row = con.execute("SELECT * FROM support_links WHERE id=?", (link_id,)).fetchone()
    return _link_dict(con, row)


def archive_support_link(con, link_id):
    link_id = _text(link_id, 80)
    row = con.execute("SELECT id FROM support_links WHERE id=?", (link_id,)).fetchone()
    if not row:
        raise ValueError("support_link_not_found")
    con.execute("UPDATE support_links SET active=0,updated_at=? WHERE id=?", (_now(), link_id))
    con.commit()
    row = con.execute("SELECT * FROM support_links WHERE id=?", (link_id,)).fetchone()
    return _link_dict(con, row)


def admin_support_links(con):
    rows = con.execute("SELECT * FROM support_links ORDER BY updated_at DESC,title ASC").fetchall()
    return {
        "schema": "egm.admin.support-links.v1",
        "links": [_link_dict(con, row) for row in rows],
        "measurementBoundary": "Clicks are measured only as aggregate navigation events. EGM4000 does not infer or claim donation amounts or completed payments.",
    }


def public_support_links(con):
    rows = con.execute("SELECT * FROM support_links WHERE active=1 ORDER BY updated_at DESC,title ASC").fetchall()
    return {
        "schema": "egm.support-links.v1",
        "links": [_link_dict(con, row, public=True) for row in rows],
        "optional": True,
        "boundary": DEFAULT_DISCLOSURE,
    }


def resolve_support_click(con, link_id):
    link_id = _text(link_id, 80)
    row = con.execute("SELECT * FROM support_links WHERE id=? AND active=1", (link_id,)).fetchone()
    if not row:
        return None
    con.execute(
        "INSERT INTO support_link_events(event_id,support_link_id,event_type,created_at) VALUES(?,?,?,?)",
        (f"se_{secrets.token_hex(12)}", row["id"], "click", _now()),
    )
    con.commit()
    return {"id": row["id"], "destinationUrl": row["destination_url"]}
