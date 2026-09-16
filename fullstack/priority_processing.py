"""C008 A077 priority processing add-on.

Priority access changes the real owner work queue for open custom-report requests.
It does not claim faster completion than the owner can actually deliver, and it
does not claim payment verification. Until billing is configured, access is only
complimentary or manually provisioned after an external/unverified process.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone

from storage import rowdict, scalar

FEATURE_ID = "A077"
ALLOWED_SOURCES = {"complimentary", "manual_external_unverified"}
PAYMENT_BOUNDARY = (
    "Priority access is not proof of payment. Until a billing provider is configured, "
    "EGM4000 records only complimentary or manual external/unverified provisioning."
)
SERVICE_BOUNDARY = (
    "Priority changes owner queue ordering for eligible open report requests. It does not "
    "guarantee a completion time, gameplay result, payout, or random outcome."
)
OPEN_STATUSES = {"requested", "accepted", "in_progress"}


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _text(value, limit=1000):
    return str(value or "").replace("\x00", "").strip()[:limit]


def migrate_priority_processing(con):
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
        """CREATE TABLE IF NOT EXISTS priority_processing_entries(
            id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL UNIQUE,
            user_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_priority_processing_user ON priority_processing_entries(user_id,updated_at)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_priority_processing_status ON priority_processing_entries(status,created_at)")
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
            "featureId": FEATURE_ID, "userId": int(user_id), "active": False,
            "status": "not_granted", "source": None, "note": "", "updatedAt": None,
            "paymentBoundary": PAYMENT_BOUNDARY,
        }
    d = rowdict(row)
    return {
        "id": d["id"], "featureId": d["feature_id"], "userId": int(d["user_id"]),
        "active": d["status"] == "active", "status": d["status"], "source": d["source"],
        "note": d["note"], "grantedBy": d["granted_by"], "createdAt": d["created_at"],
        "updatedAt": d["updated_at"], "paymentBoundary": PAYMENT_BOUNDARY,
    }


def grant_entitlement(con, user_id, source, note, granted_by):
    user_id = int(user_id)
    source = _text(source, 80)
    if source not in ALLOWED_SOURCES:
        raise ValueError("unsupported_priority_entitlement_source")
    if not _user_exists(con, user_id):
        raise ValueError("priority_entitlement_user_not_found")
    note = _text(note, 2000)
    stamp = _now()
    existing = con.execute(
        "SELECT id FROM commercial_entitlements WHERE user_id=? AND feature_id=? ORDER BY updated_at DESC LIMIT 1",
        (user_id, FEATURE_ID),
    ).fetchone()
    if existing:
        eid = existing["id"]
        con.execute(
            "UPDATE commercial_entitlements SET source=?,status='active',note=?,granted_by=?,updated_at=? WHERE id=?",
            (source, note, int(granted_by) if granted_by is not None else None, stamp, eid),
        )
    else:
        eid = f"ce_{secrets.token_hex(12)}"
        con.execute(
            "INSERT INTO commercial_entitlements(id,user_id,feature_id,source,status,note,granted_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (eid, user_id, FEATURE_ID, source, "active", note, int(granted_by) if granted_by is not None else None, stamp, stamp),
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
        raise ValueError("priority_entitlement_not_found")
    stamp = _now()
    con.execute(
        "UPDATE commercial_entitlements SET status='revoked',note=?,granted_by=?,updated_at=? WHERE id=?",
        (_text(note, 2000), int(granted_by) if granted_by is not None else None, stamp, existing["id"]),
    )
    con.execute(
        "UPDATE priority_processing_entries SET status='cancelled',updated_at=? WHERE user_id=? AND status='active'",
        (stamp, user_id),
    )
    con.commit()
    return entitlement_for_user(con, user_id)


def _request(con, user_id, request_id):
    return con.execute(
        """SELECT r.id,r.user_id,r.status,r.payment_status,r.created_at,p.title package_title
           FROM custom_report_requests r JOIN custom_report_packages p ON p.id=r.package_id
           WHERE r.id=? AND r.user_id=?""",
        (_text(request_id, 100), int(user_id)),
    ).fetchone()


def apply_priority(con, user_id, request_id):
    user_id = int(user_id)
    if not entitlement_for_user(con, user_id)["active"]:
        raise ValueError("priority_entitlement_required")
    request = _request(con, user_id, request_id)
    if not request:
        raise ValueError("priority_report_request_not_found")
    if request["status"] not in OPEN_STATUSES:
        raise ValueError("priority_requires_open_report_request")
    stamp = _now()
    existing = con.execute("SELECT id FROM priority_processing_entries WHERE request_id=?", (request["id"],)).fetchone()
    if existing:
        con.execute(
            "UPDATE priority_processing_entries SET user_id=?,status='active',updated_at=? WHERE id=?",
            (user_id, stamp, existing["id"]),
        )
        entry_id = existing["id"]
    else:
        entry_id = f"pq_{secrets.token_hex(12)}"
        con.execute(
            "INSERT INTO priority_processing_entries(id,request_id,user_id,status,created_at,updated_at) VALUES(?,?,?,?,?,?)",
            (entry_id, request["id"], user_id, "active", stamp, stamp),
        )
    con.commit()
    return priority_entry(con, user_id, request["id"])


def remove_priority(con, user_id, request_id):
    user_id = int(user_id)
    request = _request(con, user_id, request_id)
    if not request:
        raise ValueError("priority_report_request_not_found")
    existing = con.execute(
        "SELECT id FROM priority_processing_entries WHERE request_id=? AND user_id=?",
        (request["id"], user_id),
    ).fetchone()
    if not existing:
        raise ValueError("priority_entry_not_found")
    con.execute(
        "UPDATE priority_processing_entries SET status='cancelled',updated_at=? WHERE id=?",
        (_now(), existing["id"]),
    )
    con.commit()
    return priority_entry(con, user_id, request["id"])


def priority_entry(con, user_id, request_id):
    row = con.execute(
        """SELECT q.*,r.status request_status,r.payment_status,r.created_at request_created_at,p.title package_title
           FROM priority_processing_entries q
           JOIN custom_report_requests r ON r.id=q.request_id
           JOIN custom_report_packages p ON p.id=r.package_id
           WHERE q.user_id=? AND q.request_id=?""",
        (int(user_id), _text(request_id, 100)),
    ).fetchone()
    if not row:
        return None
    d = rowdict(row)
    return {
        "id": d["id"], "requestId": d["request_id"], "userId": int(d["user_id"]),
        "status": d["status"], "active": d["status"] == "active", "packageTitle": d["package_title"],
        "requestStatus": d["request_status"], "paymentStatus": d["payment_status"],
        "requestCreatedAt": d["request_created_at"], "createdAt": d["created_at"], "updatedAt": d["updated_at"],
    }


def my_priority_status(con, user_id):
    rows = con.execute(
        """SELECT r.id request_id,r.status request_status,r.payment_status,r.created_at request_created_at,
                  p.title package_title,q.id priority_id,q.status priority_status,q.created_at priority_created_at
           FROM custom_report_requests r
           JOIN custom_report_packages p ON p.id=r.package_id
           LEFT JOIN priority_processing_entries q ON q.request_id=r.id AND q.user_id=r.user_id
           WHERE r.user_id=? AND r.status IN ('requested','accepted','in_progress')
           ORDER BY r.created_at DESC""",
        (int(user_id),),
    ).fetchall()
    requests = []
    for row in rows:
        d = rowdict(row)
        requests.append({
            "requestId": d["request_id"], "packageTitle": d["package_title"],
            "requestStatus": d["request_status"], "paymentStatus": d["payment_status"],
            "requestCreatedAt": d["request_created_at"], "priority": d["priority_status"] == "active",
            "priorityStatus": d["priority_status"] or "not_applied", "priorityCreatedAt": d["priority_created_at"],
        })
    return {
        "schema": "egm.a077.priority-processing.v1", "featureId": FEATURE_ID,
        "entitlement": entitlement_for_user(con, user_id), "requests": requests,
        "paymentBoundary": PAYMENT_BOUNDARY, "serviceBoundary": SERVICE_BOUNDARY,
    }


def admin_priority_queue(con):
    rows = con.execute(
        """SELECT r.id request_id,r.user_id,r.status request_status,r.payment_status,r.created_at request_created_at,
                  p.title package_title,u.username,u.display_name,q.id priority_id,q.status priority_status,q.created_at priority_created_at
           FROM custom_report_requests r
           JOIN custom_report_packages p ON p.id=r.package_id
           JOIN users u ON u.id=r.user_id
           LEFT JOIN priority_processing_entries q ON q.request_id=r.id AND q.status='active'
           WHERE r.status IN ('requested','accepted','in_progress')
           ORDER BY CASE WHEN q.id IS NULL THEN 1 ELSE 0 END ASC,
                    CASE WHEN q.id IS NULL THEN r.created_at ELSE q.created_at END ASC,
                    r.created_at ASC"""
    ).fetchall()
    queue = []
    for idx, row in enumerate(rows, start=1):
        d = rowdict(row)
        queue.append({
            "queuePosition": idx, "requestId": d["request_id"], "userId": int(d["user_id"]),
            "username": d["username"], "displayName": d["display_name"], "packageTitle": d["package_title"],
            "requestStatus": d["request_status"], "paymentStatus": d["payment_status"],
            "requestCreatedAt": d["request_created_at"], "priority": bool(d["priority_id"]),
            "priorityCreatedAt": d["priority_created_at"],
        })
    ents = con.execute(
        """SELECT e.*,u.username,u.display_name FROM commercial_entitlements e
           JOIN users u ON u.id=e.user_id WHERE e.feature_id=? ORDER BY e.updated_at DESC""",
        (FEATURE_ID,),
    ).fetchall()
    entitlements = []
    for row in ents:
        d = rowdict(row)
        entitlements.append({
            "id": d["id"], "userId": int(d["user_id"]), "username": d["username"],
            "displayName": d["display_name"], "source": d["source"], "status": d["status"],
            "note": d["note"], "updatedAt": d["updated_at"],
        })
    return {
        "schema": "egm.admin.a077.priority-processing.v1", "featureId": FEATURE_ID,
        "queue": queue, "entitlements": entitlements, "allowedSources": sorted(ALLOWED_SOURCES),
        "paymentBoundary": PAYMENT_BOUNDARY, "serviceBoundary": SERVICE_BOUNDARY,
    }
