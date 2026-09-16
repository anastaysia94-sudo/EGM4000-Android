"""C008 commercial plan/workspace suite for A071/A073/A074/A075/A078/A085/A089.

The suite implements real access lifecycle and feature gating without claiming that
manual or externally arranged access equals provider-verified payment. Provider
confirmation is reserved for the separate billing-reconciliation capability.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import secrets

from storage import scalar, rowdict

FEATURES = {
    "advanced_analytics",      # A073
    "team_workspace",         # A074
    "research_lab",           # A075
    "premium_community",      # A078
    "enterprise_workspace",   # A085
    "founder_analytics",       # A089
}
PLAN_STATUSES = {"draft", "active", "archived"}
SUBSCRIPTION_STATUSES = {"active", "cancelled", "expired"}
REQUEST_STATUSES = {"pending", "approved", "declined"}
MANUAL_SOURCES = {"complimentary", "external_unverified"}
EVIDENCE_LABELS = {"exact_telemetry", "observed_evidence", "estimate", "correlation", "hypothesis", "unknown"}


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _text(value, limit=1000):
    return str(value or "").replace("\x00", "").strip()[:limit]


def _json_list(value):
    if isinstance(value, str):
        value = [x.strip() for x in value.replace(",", "\n").splitlines() if x.strip()]
    if not isinstance(value, list):
        return []
    out = []
    for item in value:
        item = _text(item, 80).lower()
        if item in FEATURES and item not in out:
            out.append(item)
    return out


def migrate_commercial_suite(con):
    statements = [
        """CREATE TABLE IF NOT EXISTS commercial_plans(
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            price_label TEXT NOT NULL DEFAULT '',
            features_json TEXT NOT NULL DEFAULT '[]',
            seat_limit INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS commercial_plan_requests(
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            plan_id TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS commercial_subscriptions(
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            plan_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            source TEXT NOT NULL,
            source_ref TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            starts_at TEXT NOT NULL,
            ends_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS commercial_research_notes(
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL DEFAULT '',
            evidence_label TEXT NOT NULL DEFAULT 'hypothesis',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS commercial_premium_posts(
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS commercial_workspaces(
            id TEXT PRIMARY KEY,
            owner_user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            kind TEXT NOT NULL,
            seat_limit INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS commercial_workspace_members(
            workspace_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL DEFAULT 'member',
            created_at TEXT NOT NULL,
            PRIMARY KEY(workspace_id,user_id)
        )""",
        "CREATE INDEX IF NOT EXISTS idx_commercial_requests_user ON commercial_plan_requests(user_id,created_at)",
        "CREATE INDEX IF NOT EXISTS idx_commercial_sub_user ON commercial_subscriptions(user_id,status)",
        "CREATE INDEX IF NOT EXISTS idx_commercial_research_user ON commercial_research_notes(user_id,updated_at)",
        "CREATE INDEX IF NOT EXISTS idx_commercial_premium_time ON commercial_premium_posts(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_commercial_workspaces_owner ON commercial_workspaces(owner_user_id,status)",
    ]
    for statement in statements:
        con.execute(statement)
    con.commit()


def _plan_dict(row):
    try:
        features = json.loads(row["features_json"] or "[]")
    except Exception:
        features = []
    return {
        "id": row["id"], "title": row["title"], "description": row["description"],
        "priceLabel": row["price_label"], "features": features,
        "seatLimit": int(row["seat_limit"]), "status": row["status"],
        "createdAt": row["created_at"], "updatedAt": row["updated_at"],
    }


def save_plan(con, payload):
    if not isinstance(payload, dict):
        raise ValueError("invalid_plan_payload")
    plan_id = _text(payload.get("id"), 80) or f"plan_{secrets.token_hex(10)}"
    title = _text(payload.get("title"), 180)
    if not title:
        raise ValueError("plan_title_required")
    status = _text(payload.get("status") or "draft", 20).lower()
    if status not in PLAN_STATUSES:
        raise ValueError("invalid_plan_status")
    features = _json_list(payload.get("features"))
    seat_limit = int(payload.get("seat_limit") or 1)
    if seat_limit < 1 or seat_limit > 500:
        raise ValueError("invalid_seat_limit")
    stamp = _now()
    existing = con.execute("SELECT id FROM commercial_plans WHERE id=?", (plan_id,)).fetchone()
    values = (
        title, _text(payload.get("description"), 3000), _text(payload.get("price_label"), 120),
        json.dumps(features), seat_limit, status, stamp, plan_id,
    )
    if existing:
        con.execute("UPDATE commercial_plans SET title=?,description=?,price_label=?,features_json=?,seat_limit=?,status=?,updated_at=? WHERE id=?", values)
    else:
        con.execute(
            "INSERT INTO commercial_plans(id,title,description,price_label,features_json,seat_limit,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (plan_id, *values[:-1], stamp),
        )
    con.commit()
    return _plan_dict(con.execute("SELECT * FROM commercial_plans WHERE id=?", (plan_id,)).fetchone())


def public_plans(con):
    rows = con.execute("SELECT * FROM commercial_plans WHERE status='active' ORDER BY title,id").fetchall()
    return {
        "schema": "egm.commercial-plans.v1",
        "plans": [_plan_dict(r) for r in rows],
        "billingBoundary": "Plan requests do not prove payment. Access is inactive until an owner grant or a separately verified billing-provider event activates it.",
    }


def admin_plans(con):
    rows = con.execute("SELECT * FROM commercial_plans ORDER BY updated_at DESC,title").fetchall()
    return [_plan_dict(r) for r in rows]


def request_plan(con, user_id, plan_id, note=""):
    plan_id = _text(plan_id, 80)
    if not con.execute("SELECT id FROM commercial_plans WHERE id=? AND status='active'", (plan_id,)).fetchone():
        raise ValueError("plan_not_available")
    if con.execute("SELECT id FROM commercial_plan_requests WHERE user_id=? AND plan_id=? AND status='pending'", (user_id, plan_id)).fetchone():
        raise ValueError("plan_request_already_pending")
    rid = f"pr_{secrets.token_hex(10)}"; stamp = _now()
    con.execute(
        "INSERT INTO commercial_plan_requests(id,user_id,plan_id,note,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
        (rid, user_id, plan_id, _text(note, 3000), "pending", stamp, stamp),
    )
    con.commit()
    return rid


def _subscription_dict(row):
    return {
        "id": row["id"], "userId": int(row["user_id"]), "planId": row["plan_id"],
        "planTitle": row.get("plan_title", "") if isinstance(row, dict) else (row["plan_title"] if "plan_title" in row.keys() else ""),
        "status": row["status"], "source": row["source"], "sourceRef": row["source_ref"],
        "note": row["note"], "startsAt": row["starts_at"], "endsAt": row["ends_at"],
        "createdAt": row["created_at"], "updatedAt": row["updated_at"],
    }


def grant_subscription(con, user_id, plan_id, source="complimentary", note="", ends_at=None, source_ref=""):
    source = _text(source, 40).lower()
    if source not in MANUAL_SOURCES:
        raise ValueError("unsupported_manual_subscription_source")
    plan_id = _text(plan_id, 80)
    if not con.execute("SELECT id FROM users WHERE id=? AND status='active'", (user_id,)).fetchone():
        raise ValueError("subscription_user_not_found")
    if not con.execute("SELECT id FROM commercial_plans WHERE id=? AND status='active'", (plan_id,)).fetchone():
        raise ValueError("subscription_plan_not_available")
    stamp = _now()
    existing = con.execute("SELECT id FROM commercial_subscriptions WHERE user_id=? AND plan_id=? AND status='active'", (user_id, plan_id)).fetchone()
    if existing:
        sid = existing["id"]
        con.execute("UPDATE commercial_subscriptions SET source=?,source_ref=?,note=?,ends_at=?,updated_at=? WHERE id=?", (source, _text(source_ref, 200), _text(note, 2000), ends_at, stamp, sid))
    else:
        sid = f"sub_{secrets.token_hex(10)}"
        con.execute(
            "INSERT INTO commercial_subscriptions(id,user_id,plan_id,status,source,source_ref,note,starts_at,ends_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (sid, user_id, plan_id, "active", source, _text(source_ref, 200), _text(note, 2000), stamp, ends_at, stamp, stamp),
        )
    con.execute("UPDATE commercial_plan_requests SET status='approved',updated_at=? WHERE user_id=? AND plan_id=? AND status='pending'", (stamp, user_id, plan_id))
    con.commit()
    return sid


def revoke_subscription(con, subscription_id):
    sid = _text(subscription_id, 80)
    if not con.execute("SELECT id FROM commercial_subscriptions WHERE id=?", (sid,)).fetchone():
        raise ValueError("subscription_not_found")
    con.execute("UPDATE commercial_subscriptions SET status='cancelled',updated_at=? WHERE id=?", (_now(), sid)); con.commit()


def resolve_plan_request(con, request_id, status):
    status = _text(status, 20).lower()
    if status not in {"approved", "declined"}:
        raise ValueError("invalid_plan_request_status")
    if not con.execute("SELECT id FROM commercial_plan_requests WHERE id=?", (_text(request_id, 80),)).fetchone():
        raise ValueError("plan_request_not_found")
    con.execute("UPDATE commercial_plan_requests SET status=?,updated_at=? WHERE id=?", (status, _now(), _text(request_id, 80))); con.commit()


def _active_sub_rows(con, user_id):
    stamp = _now()
    return con.execute(
        """SELECT s.*,p.title plan_title,p.features_json,p.seat_limit
           FROM commercial_subscriptions s JOIN commercial_plans p ON p.id=s.plan_id
           WHERE s.user_id=? AND s.status='active' AND p.status='active' AND (s.ends_at IS NULL OR s.ends_at='' OR s.ends_at>?)
           ORDER BY s.created_at DESC""",
        (user_id, stamp),
    ).fetchall()


def has_feature(con, user_id, feature):
    feature = _text(feature, 80).lower()
    if feature not in FEATURES:
        return False
    for row in _active_sub_rows(con, user_id):
        try: features = json.loads(row["features_json"] or "[]")
        except Exception: features = []
        if feature in features:
            return True
    return False


def feature_seat_limit(con, user_id, feature):
    limit = 0
    for row in _active_sub_rows(con, user_id):
        try: features = json.loads(row["features_json"] or "[]")
        except Exception: features = []
        if feature in features:
            limit = max(limit, int(row["seat_limit"] or 1))
    return limit


def my_commercial_status(con, user_id):
    subs = [_subscription_dict(rowdict(r)) for r in _active_sub_rows(con, user_id)]
    requests = con.execute(
        """SELECT r.*,p.title plan_title FROM commercial_plan_requests r JOIN commercial_plans p ON p.id=r.plan_id
           WHERE r.user_id=? ORDER BY r.created_at DESC""", (user_id,)
    ).fetchall()
    return {
        "schema": "egm.commercial-status.v1",
        "subscriptions": subs,
        "features": {f: has_feature(con, user_id, f) for f in sorted(FEATURES)},
        "requests": [{"id":r["id"],"planId":r["plan_id"],"planTitle":r["plan_title"],"status":r["status"],"note":r["note"],"createdAt":r["created_at"]} for r in requests],
        "billingBoundary": "Manual/complimentary and external-unverified access are access states, not proof of provider-confirmed payment.",
    }


def advanced_analytics(con, user_id):
    if not has_feature(con, user_id, "advanced_analytics"):
        raise PermissionError("advanced_analytics_entitlement_required")
    rows = con.execute("SELECT * FROM gameplay_sessions WHERE user_id=? ORDER BY started_at,id", (user_id,)).fetchall()
    by_platform = {}
    total_duration=total_shots=total_hits=0; total_spend=total_payout=0.0
    for row in rows:
        p = row["platform"]; d = by_platform.setdefault(p,{"sessions":0,"durationMin":0,"shots":0,"hits":0,"spend":0.0,"payout":0.0})
        duration=int(row["duration_min"] or 0); shots=int(row["shots"] or 0); hits=int(row["hits"] or 0); spend=float(row["spend"] or 0); payout=float(row["payout"] or 0)
        d["sessions"]+=1;d["durationMin"]+=duration;d["shots"]+=shots;d["hits"]+=hits;d["spend"]+=spend;d["payout"]+=payout
        total_duration+=duration;total_shots+=shots;total_hits+=hits;total_spend+=spend;total_payout+=payout
    for d in by_platform.values():
        d["observedHitRate"] = round(d["hits"]/d["shots"],4) if d["shots"] else None
        d["recordedNet"] = round(d["payout"]-d["spend"],2)
        d["spend"] = round(d["spend"],2); d["payout"] = round(d["payout"],2)
    return {
        "schema":"egm.advanced-analytics.v1","sessions":len(rows),"durationMin":total_duration,
        "shots":total_shots,"hits":total_hits,"observedHitRate":round(total_hits/total_shots,4) if total_shots else None,
        "recordedSpend":round(total_spend,2),"recordedPayout":round(total_payout,2),"recordedNet":round(total_payout-total_spend,2),
        "byPlatform":by_platform,
        "boundary":"Historical recorded evidence only. These summaries do not predict random outcomes, future payout, or profit.",
    }


def save_research_note(con, user_id, payload):
    if not has_feature(con, user_id, "research_lab"):
        raise PermissionError("research_lab_entitlement_required")
    nid = _text(payload.get("id"),80) or f"rn_{secrets.token_hex(10)}"; title=_text(payload.get("title"),180)
    if not title: raise ValueError("research_title_required")
    label=_text(payload.get("evidence_label") or "hypothesis",40).lower()
    if label not in EVIDENCE_LABELS: raise ValueError("invalid_evidence_label")
    stamp=_now(); existing=con.execute("SELECT id FROM commercial_research_notes WHERE id=? AND user_id=?",(nid,user_id)).fetchone()
    if existing: con.execute("UPDATE commercial_research_notes SET title=?,body=?,evidence_label=?,updated_at=? WHERE id=? AND user_id=?",(title,_text(payload.get("body"),8000),label,stamp,nid,user_id))
    else: con.execute("INSERT INTO commercial_research_notes(id,user_id,title,body,evidence_label,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",(nid,user_id,title,_text(payload.get("body"),8000),label,stamp,stamp))
    con.commit(); return nid


def research_notes(con,user_id):
    if not has_feature(con,user_id,"research_lab"): raise PermissionError("research_lab_entitlement_required")
    rows=con.execute("SELECT * FROM commercial_research_notes WHERE user_id=? ORDER BY updated_at DESC",(user_id,)).fetchall()
    return {"schema":"egm.research-lab.v1","notes":[dict(rowdict(r)) for r in rows],"boundary":"Research notes are private working hypotheses/evidence labels, not hidden-game-state claims or future-outcome predictions."}


def create_premium_post(con,user_id,payload):
    if not has_feature(con,user_id,"premium_community"): raise PermissionError("premium_community_entitlement_required")
    title=_text(payload.get("title"),180);body=_text(payload.get("body"),6000)
    if not title or not body: raise ValueError("premium_post_content_required")
    pid=f"pc_{secrets.token_hex(10)}";stamp=_now();con.execute("INSERT INTO commercial_premium_posts(id,user_id,title,body,created_at,updated_at) VALUES(?,?,?,?,?,?)",(pid,user_id,title,body,stamp,stamp));con.commit();return pid


def premium_posts(con,user_id):
    if not has_feature(con,user_id,"premium_community"): raise PermissionError("premium_community_entitlement_required")
    rows=con.execute("""SELECT p.*,u.display_name FROM commercial_premium_posts p JOIN users u ON u.id=p.user_id ORDER BY p.created_at DESC LIMIT 100""").fetchall()
    return {"schema":"egm.premium-community.v1","posts":[dict(rowdict(r)) for r in rows],"boundary":"Membership controls access only; it never changes gameplay evidence, probabilities, or outcomes."}


def create_workspace(con,user_id,name,kind="team"):
    kind=_text(kind,20).lower(); feature="enterprise_workspace" if kind=="enterprise" else "team_workspace"
    if kind not in {"team","enterprise"}: raise ValueError("invalid_workspace_kind")
    limit=feature_seat_limit(con,user_id,feature)
    if limit < 1: raise PermissionError(f"{feature}_entitlement_required")
    name=_text(name,180)
    if not name: raise ValueError("workspace_name_required")
    wid=f"ws_{secrets.token_hex(10)}";stamp=_now();con.execute("INSERT INTO commercial_workspaces(id,owner_user_id,name,kind,seat_limit,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",(wid,user_id,name,kind,limit,"active",stamp,stamp));con.execute("INSERT INTO commercial_workspace_members(workspace_id,user_id,role,created_at) VALUES(?,?,?,?)",(wid,user_id,"owner",stamp));con.commit();return wid


def add_workspace_member(con, owner_user_id, workspace_id, member_user_id, role="member"):
    role=_text(role,20).lower()
    if role not in {"coach","member"}: raise ValueError("invalid_workspace_role")
    w=con.execute("SELECT * FROM commercial_workspaces WHERE id=? AND owner_user_id=? AND status='active'",(_text(workspace_id,80),owner_user_id)).fetchone()
    if not w: raise ValueError("workspace_not_found")
    if not con.execute("SELECT id FROM users WHERE id=? AND status='active'",(member_user_id,)).fetchone(): raise ValueError("workspace_member_not_found")
    count=int(scalar(con,"SELECT COUNT(*) FROM commercial_workspace_members WHERE workspace_id=?",(w["id"],)) or 0)
    exists=con.execute("SELECT user_id FROM commercial_workspace_members WHERE workspace_id=? AND user_id=?",(w["id"],member_user_id)).fetchone()
    if not exists and count>=int(w["seat_limit"]): raise ValueError("workspace_seat_limit_reached")
    if exists: con.execute("UPDATE commercial_workspace_members SET role=? WHERE workspace_id=? AND user_id=?",(role,w["id"],member_user_id))
    else: con.execute("INSERT INTO commercial_workspace_members(workspace_id,user_id,role,created_at) VALUES(?,?,?,?)",(w["id"],member_user_id,role,_now()))
    con.commit()


def my_workspaces(con,user_id):
    rows=con.execute("""SELECT w.*,m.role membership_role FROM commercial_workspaces w JOIN commercial_workspace_members m ON m.workspace_id=w.id WHERE m.user_id=? AND w.status='active' ORDER BY w.updated_at DESC""",(user_id,)).fetchall(); out=[]
    for r in rows:
        d=dict(rowdict(r)); members=con.execute("""SELECT m.user_id,m.role,u.display_name FROM commercial_workspace_members m JOIN users u ON u.id=m.user_id WHERE m.workspace_id=? ORDER BY m.role,u.display_name""",(r["id"],)).fetchall();d["members"]=[dict(rowdict(x)) for x in members];out.append(d)
    return {"schema":"egm.commercial-workspaces.v1","workspaces":out,"boundary":"Workspace access controls collaboration only; it does not expose other users' private evidence unless separately shared through an authorized product flow."}


def founder_analytics(con,user_id):
    if not has_feature(con,user_id,"founder_analytics"): raise PermissionError("founder_analytics_entitlement_required")
    plan_rows=con.execute("SELECT id,title,status FROM commercial_plans ORDER BY title").fetchall(); plans=[]
    for p in plan_rows:
        active=int(scalar(con,"SELECT COUNT(*) FROM commercial_subscriptions WHERE plan_id=? AND status='active'",(p["id"],)) or 0); pending=int(scalar(con,"SELECT COUNT(*) FROM commercial_plan_requests WHERE plan_id=? AND status='pending'",(p["id"],)) or 0);plans.append({"id":p["id"],"title":p["title"],"status":p["status"],"activeAccess":active,"pendingRequests":pending})
    return {"schema":"egm.founder-commercial-analytics.v1","plans":plans,"totals":{"activeSubscriptions":int(scalar(con,"SELECT COUNT(*) FROM commercial_subscriptions WHERE status='active'") or 0),"workspaces":int(scalar(con,"SELECT COUNT(*) FROM commercial_workspaces WHERE status='active'") or 0),"researchNotes":int(scalar(con,"SELECT COUNT(*) FROM commercial_research_notes") or 0),"premiumPosts":int(scalar(con,"SELECT COUNT(*) FROM commercial_premium_posts") or 0)},"boundary":"Commercial access analytics describe product usage/access state only. Revenue is not inferred from manual or external-unverified access."}


def admin_commercial_snapshot(con):
    requests=con.execute("""SELECT r.*,u.display_name,p.title plan_title FROM commercial_plan_requests r JOIN users u ON u.id=r.user_id JOIN commercial_plans p ON p.id=r.plan_id ORDER BY r.created_at DESC""").fetchall()
    subs=con.execute("""SELECT s.*,u.display_name,p.title plan_title FROM commercial_subscriptions s JOIN users u ON u.id=s.user_id JOIN commercial_plans p ON p.id=s.plan_id ORDER BY s.updated_at DESC""").fetchall()
    return {"schema":"egm.admin.commercial-suite.v1","plans":admin_plans(con),"requests":[dict(rowdict(r)) for r in requests],"subscriptions":[dict(rowdict(r)) for r in subs],"boundary":"Owner grants marked complimentary or external_unverified do not certify a provider payment."}
