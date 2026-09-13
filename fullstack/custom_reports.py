"""C008 A087 custom report package workflow.

This module provides a real request/fulfillment workflow without pretending that
external payment has been verified. Billing confirmation remains provider-backed.
"""
from __future__ import annotations

from datetime import datetime, timezone
import ipaddress
import json
import secrets
from urllib.parse import urlparse

from storage import scalar

PACKAGE_STATUSES = {"draft", "active", "archived"}
REQUEST_STATUSES = {"requested", "accepted", "in_progress", "delivered", "cancelled"}
PAYMENT_STATUSES = {"external_unverified", "not_required", "provider_verified"}


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _text(value, limit=500):
    return str(value or "").replace("\x00", "").strip()[:limit]


def _delivery_url(value):
    value = _text(value, 1200)
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme.lower() != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("https_delivery_url_required")
    host = parsed.hostname.lower().rstrip(".")
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise ValueError("private_delivery_url_not_allowed")
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("private_delivery_url_not_allowed")
    except ValueError as exc:
        if str(exc) == "private_delivery_url_not_allowed":
            raise
    return value


def migrate_custom_reports(con):
    statements = [
        """CREATE TABLE IF NOT EXISTS custom_report_packages(
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            deliverables_json TEXT NOT NULL DEFAULT '[]',
            price_label TEXT NOT NULL DEFAULT '',
            turnaround_label TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS custom_report_requests(
            id TEXT PRIMARY KEY,
            package_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            request_note TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'requested',
            payment_status TEXT NOT NULL DEFAULT 'external_unverified',
            owner_note TEXT NOT NULL DEFAULT '',
            delivery_note TEXT NOT NULL DEFAULT '',
            delivery_url TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_custom_report_requests_user ON custom_report_requests(user_id,created_at)",
        "CREATE INDEX IF NOT EXISTS idx_custom_report_requests_status ON custom_report_requests(status,created_at)",
    ]
    for statement in statements:
        con.execute(statement)
    con.commit()


def _deliverables(value):
    if isinstance(value, str):
        value = [x.strip() for x in value.split("\n") if x.strip()]
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        clean = _text(item, 240)
        if clean and clean not in out:
            out.append(clean)
    return out[:20]


def _package_dict(row):
    try:
        deliverables = json.loads(row["deliverables_json"] or "[]")
    except Exception:
        deliverables = []
    if not isinstance(deliverables, list):
        deliverables = []
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "deliverables": deliverables,
        "priceLabel": row["price_label"],
        "turnaroundLabel": row["turnaround_label"],
        "status": row["status"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def save_package(con, payload):
    if not isinstance(payload, dict):
        raise ValueError("invalid_report_package_payload")
    package_id = _text(payload.get("id"), 80) or f"rp_{secrets.token_hex(12)}"
    title = _text(payload.get("title"), 180)
    description = _text(payload.get("description"), 3000)
    price_label = _text(payload.get("price_label"), 120)
    turnaround = _text(payload.get("turnaround_label"), 120)
    status = _text(payload.get("status") or "draft", 20).lower()
    if not title:
        raise ValueError("report_package_title_required")
    if status not in PACKAGE_STATUSES:
        raise ValueError("invalid_report_package_status")
    deliverables = _deliverables(payload.get("deliverables"))
    stamp = _now()
    existing = con.execute("SELECT id FROM custom_report_packages WHERE id=?", (package_id,)).fetchone()
    if existing:
        con.execute(
            """UPDATE custom_report_packages
               SET title=?,description=?,deliverables_json=?,price_label=?,turnaround_label=?,status=?,updated_at=?
               WHERE id=?""",
            (title, description, json.dumps(deliverables), price_label, turnaround, status, stamp, package_id),
        )
    else:
        con.execute(
            """INSERT INTO custom_report_packages(
                 id,title,description,deliverables_json,price_label,turnaround_label,status,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (package_id, title, description, json.dumps(deliverables), price_label, turnaround, status, stamp, stamp),
        )
    con.commit()
    row = con.execute("SELECT * FROM custom_report_packages WHERE id=?", (package_id,)).fetchone()
    return _package_dict(row)


def public_packages(con):
    rows = con.execute("SELECT * FROM custom_report_packages WHERE status='active' ORDER BY updated_at DESC,title ASC").fetchall()
    return {
        "schema": "egm.custom-report-packages.v1",
        "packages": [_package_dict(row) for row in rows],
        "billingBoundary": "Submitting a report request does not prove payment. Payment remains external/unverified until a configured provider verifies it.",
    }


def admin_packages(con):
    rows = con.execute("SELECT * FROM custom_report_packages ORDER BY updated_at DESC,title ASC").fetchall()
    return [_package_dict(row) for row in rows]


def create_request(con, user_id, payload):
    if not isinstance(payload, dict):
        raise ValueError("invalid_report_request_payload")
    package_id = _text(payload.get("package_id"), 80)
    package = con.execute("SELECT * FROM custom_report_packages WHERE id=? AND status='active'", (package_id,)).fetchone()
    if not package:
        raise ValueError("report_package_not_available")
    existing = con.execute(
        "SELECT id FROM custom_report_requests WHERE package_id=? AND user_id=? AND status IN ('requested','accepted','in_progress')",
        (package_id, user_id),
    ).fetchone()
    if existing:
        raise ValueError("active_report_request_exists")
    request_id = f"rr_{secrets.token_hex(12)}"
    note = _text(payload.get("request_note"), 4000)
    stamp = _now()
    con.execute(
        """INSERT INTO custom_report_requests(
             id,package_id,user_id,request_note,status,payment_status,owner_note,delivery_note,delivery_url,created_at,updated_at
           ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (request_id, package_id, user_id, note, "requested", "external_unverified", "", "", "", stamp, stamp),
    )
    con.commit()
    return get_request(con, request_id, user_id=user_id)


def _request_dict(row):
    return {
        "id": row["id"],
        "packageId": row["package_id"],
        "userId": row["user_id"],
        "packageTitle": row["package_title"],
        "priceLabel": row["price_label"],
        "turnaroundLabel": row["turnaround_label"],
        "requestNote": row["request_note"],
        "status": row["status"],
        "paymentStatus": row["payment_status"],
        "ownerNote": row["owner_note"],
        "deliveryNote": row["delivery_note"],
        "deliveryUrl": row["delivery_url"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def get_request(con, request_id, user_id=None):
    sql = """SELECT r.*,p.title package_title,p.price_label,p.turnaround_label
             FROM custom_report_requests r JOIN custom_report_packages p ON p.id=r.package_id
             WHERE r.id=?"""
    params = [request_id]
    if user_id is not None:
        sql += " AND r.user_id=?"
        params.append(user_id)
    row = con.execute(sql, tuple(params)).fetchone()
    return _request_dict(row) if row else None


def my_requests(con, user_id):
    rows = con.execute(
        """SELECT r.*,p.title package_title,p.price_label,p.turnaround_label
           FROM custom_report_requests r JOIN custom_report_packages p ON p.id=r.package_id
           WHERE r.user_id=? ORDER BY r.created_at DESC""",
        (user_id,),
    ).fetchall()
    return {
        "schema": "egm.my-custom-report-requests.v1",
        "requests": [_request_dict(row) for row in rows],
    }


def admin_requests(con):
    rows = con.execute(
        """SELECT r.*,p.title package_title,p.price_label,p.turnaround_label
           FROM custom_report_requests r JOIN custom_report_packages p ON p.id=r.package_id
           ORDER BY r.created_at DESC"""
    ).fetchall()
    return {
        "schema": "egm.admin.custom-report-requests.v1",
        "requests": [_request_dict(row) for row in rows],
        "summary": {
            "total": len(rows),
            "open": sum(1 for row in rows if row["status"] in ("requested", "accepted", "in_progress")),
            "delivered": sum(1 for row in rows if row["status"] == "delivered"),
        },
    }


def update_request(con, request_id, payload):
    request_id = _text(request_id, 80)
    existing = con.execute("SELECT id FROM custom_report_requests WHERE id=?", (request_id,)).fetchone()
    if not existing:
        raise ValueError("report_request_not_found")
    status = _text(payload.get("status"), 30).lower()
    payment_status = _text(payload.get("payment_status") or "external_unverified", 40).lower()
    if status not in REQUEST_STATUSES:
        raise ValueError("invalid_report_request_status")
    if payment_status not in PAYMENT_STATUSES:
        raise ValueError("invalid_report_payment_status")
    if payment_status == "provider_verified" and not bool(payload.get("provider_verification")):
        raise ValueError("provider_verification_required")
    owner_note = _text(payload.get("owner_note"), 4000)
    delivery_note = _text(payload.get("delivery_note"), 6000)
    delivery_url = _delivery_url(payload.get("delivery_url"))
    if status == "delivered" and not (delivery_note or delivery_url):
        raise ValueError("delivery_content_required")
    con.execute(
        """UPDATE custom_report_requests
           SET status=?,payment_status=?,owner_note=?,delivery_note=?,delivery_url=?,updated_at=?
           WHERE id=?""",
        (status, payment_status, owner_note, delivery_note, delivery_url, _now(), request_id),
    )
    con.commit()
    return get_request(con, request_id)
