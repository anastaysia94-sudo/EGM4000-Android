"""C009 return-user workspace: persisted preferences, safe goals, media review, and evidence-derived analytics."""
from __future__ import annotations
from datetime import datetime, timezone
import json
from storage import scalar

SAFE_GOAL_TYPES = {
    "tip_reviews": {"title": "Review coaching evidence", "unit": "rated tips"},
    "reflection_notes": {"title": "Write reflection notes", "unit": "notes"},
    "evidence_days": {"title": "Build evidence consistency", "unit": "recorded days"},
}
DEFAULT_PREFERENCES = {
    "notifications_enabled": True,
    "tip_notifications": True,
    "review_notifications": True,
    "pause_until": "",
}


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _loads(raw, fallback=None):
    try:
        value = json.loads(raw or "")
        return value
    except Exception:
        return {} if fallback is None else fallback


def migrate_return_workspace(con):
    statements = [
        """CREATE TABLE IF NOT EXISTS return_tip_feedback(
            user_id INTEGER NOT NULL,
            tip_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            PRIMARY KEY(user_id,tip_id)
        )""",
        """CREATE TABLE IF NOT EXISTS return_goals(
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            goal_type TEXT NOT NULL,
            target INTEGER NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS return_preferences(
            user_id INTEGER PRIMARY KEY,
            notifications_enabled INTEGER NOT NULL DEFAULT 1,
            tip_notifications INTEGER NOT NULL DEFAULT 1,
            review_notifications INTEGER NOT NULL DEFAULT 1,
            pause_until TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS return_notes(
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            note_type TEXT NOT NULL DEFAULT 'reflection',
            body TEXT NOT NULL,
            tags_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS return_media(
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            file_name TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            data_b64 TEXT NOT NULL DEFAULT '',
            byte_size INTEGER NOT NULL DEFAULT 0,
            review_note TEXT NOT NULL DEFAULT '',
            tags_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS return_saved_views(
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            config_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
    ]
    for statement in statements:
        con.execute(statement)
    con.commit()


def load_preferences(con, user_id):
    row = con.execute(
        """SELECT notifications_enabled,tip_notifications,review_notifications,pause_until
           FROM return_preferences WHERE user_id=?""",
        (user_id,),
    ).fetchone()
    if not row:
        return dict(DEFAULT_PREFERENCES)
    return {
        "notifications_enabled": bool(row["notifications_enabled"]),
        "tip_notifications": bool(row["tip_notifications"]),
        "review_notifications": bool(row["review_notifications"]),
        "pause_until": row["pause_until"] or "",
    }


def smart_tags(text="", kind="", platform=""):
    hay = f"{text} {kind} {platform}".lower()
    tags = []
    rules = [
        ("evidence", ("evidence", "review", "compare", "confidence")),
        ("pacing", ("pace", "shots", "speed", "rapid")),
        ("breaks", ("break", "pause", "fatigue", "tired")),
        ("bankroll", ("bankroll", "spend", "credit", "drawdown")),
        ("targets", ("target", "enemy", "fish", "boss")),
        ("weapons", ("weapon", "cannon", "level", "shot cost")),
        ("reflection", ("note", "reflection", "learned", "journal")),
        ("screenshot", ("screenshot", "image", "png", "jpeg", "webp")),
        ("video", ("video", "webm", "mp4")),
        ("voice", ("voice", "audio", "recording", "ogg")),
    ]
    for tag, words in rules:
        if any(word in hay for word in words):
            tags.append(tag)
    if platform:
        cleaned = str(platform).strip().lower().replace(" ", "-")
        if cleaned and cleaned not in tags:
            tags.append(cleaned)
    return tags[:8]


def _payload(row):
    raw = row["payload_json"] if "payload_json" in row.keys() else "{}"
    value = _loads(raw, {})
    return value if isinstance(value, dict) else {}


def _group_sessions(sessions, key_fn):
    groups = {}
    for row in sessions:
        key = key_fn(row)
        if not key:
            continue
        g = groups.setdefault(key, {"sessions": 0, "shots": 0, "hits": 0, "duration": 0.0, "spend": 0.0})
        g["sessions"] += 1
        g["shots"] += int(row["shots"] or 0)
        g["hits"] += int(row["hits"] or 0)
        g["duration"] += float(row["duration_min"] or 0)
        g["spend"] += float(row["spend"] or 0)
    out = []
    for name, g in groups.items():
        shots = g["shots"]
        out.append({
            "name": name,
            "sessions": g["sessions"],
            "hitRate": round(g["hits"] / shots, 4) if shots else None,
            "avgDurationMin": round(g["duration"] / g["sessions"], 1) if g["sessions"] else None,
            "costPerShot": round(g["spend"] / shots, 4) if shots else None,
        })
    return sorted(out, key=lambda x: (-x["sessions"], x["name"]))


def _event_dimension(events, keys):
    grouped = {}
    for row in events:
        payload = _payload(row)
        value = next((payload.get(k) for k in keys if payload.get(k) not in (None, "")), None)
        if value is None:
            continue
        label = str(value)[:80]
        g = grouped.setdefault(label, {"events": 0, "attempts": 0, "successes": 0, "cost": 0.0})
        g["events"] += 1
        event_type = str(row["event_type"] or "").lower()
        if event_type in ("shot_fired", "shot"):
            g["attempts"] += 1
        success = event_type in ("hit", "target_hit", "kill", "target_killed", "target_destroyed")
        if payload.get("hit") is True or str(payload.get("result", "")).lower() in ("hit", "kill", "success"):
            success = True
        if success:
            g["successes"] += 1
        for key in ("cost", "shot_cost", "spend"):
            if payload.get(key) not in (None, ""):
                try:
                    g["cost"] += float(payload[key])
                except Exception:
                    pass
                break
    out = []
    for name, g in grouped.items():
        attempts = g["attempts"] or g["events"]
        out.append({
            "name": name,
            "events": g["events"],
            "attempts": g["attempts"],
            "successes": g["successes"],
            "successRate": round(g["successes"] / attempts, 4) if attempts else None,
            "recordedCost": round(g["cost"], 4),
        })
    return sorted(out, key=lambda x: (-x["events"], x["name"]))


def _goal_current(con, user_id, goal_type):
    if goal_type == "tip_reviews":
        return int(scalar(con, "SELECT COUNT(*) FROM return_tip_feedback WHERE user_id=?", (user_id,)) or 0)
    if goal_type == "reflection_notes":
        return int(scalar(con, "SELECT COUNT(*) FROM return_notes WHERE user_id=?", (user_id,)) or 0)
    if goal_type == "evidence_days":
        dates = set()
        for table, col in (("gameplay_sessions", "started_at"), ("live_sessions", "started_at")):
            rows = con.execute(f"SELECT {col} FROM {table} WHERE user_id=?", (user_id,)).fetchall()
            dates.update(str(r[col])[:10] for r in rows if r[col])
        return len(dates)
    return 0


def build_return_workspace(con, user_id):
    migrate_return_workspace(con)
    sessions = con.execute(
        """SELECT id,platform,started_at,duration_min,spend,payout,shots,hits
           FROM gameplay_sessions WHERE user_id=? ORDER BY started_at DESC LIMIT 250""",
        (user_id,),
    ).fetchall()
    events = con.execute(
        """SELECT n.event_type,n.payload_json,n.evidence_type,n.confidence,n.platform,n.event_time
           FROM normalized_events n WHERE n.user_id=? ORDER BY n.event_time DESC LIMIT 3000""",
        (user_id,),
    ).fetchall()
    tips = con.execute(
        """SELECT t.id,t.title,t.body,t.confidence,t.created_at,f.rating,f.note rating_note
           FROM tips t LEFT JOIN return_tip_feedback f ON f.tip_id=t.id AND f.user_id=t.user_id
           WHERE t.user_id=? ORDER BY t.id DESC LIMIT 30""",
        (user_id,),
    ).fetchall()

    best = None
    for row in sessions:
        shots = int(row["shots"] or 0)
        hits = int(row["hits"] or 0)
        if shots <= 0:
            continue
        hit_rate = hits / shots
        candidate = {
            "sessionId": row["id"],
            "platform": row["platform"],
            "startedAt": row["started_at"],
            "shots": shots,
            "hits": hits,
            "hitRate": round(hit_rate, 4),
        }
        if best is None or candidate["hitRate"] > best["hitRate"]:
            best = candidate

    target_eff = _event_dimension(events, ("target", "target_type", "enemy", "enemy_type"))
    weapon_eff = _event_dimension(events, ("weapon", "weapon_level", "cannon", "cannon_level"))
    denom_eff = _event_dimension(events, ("denomination", "denom", "bet", "bet_level"))
    if not weapon_eff:
        weapon_eff = [
            {**row, "source": "session aggregate; weapon not recorded"}
            for row in _group_sessions(sessions, lambda r: str(r["platform"] or "Unknown platform"))
        ]

    def time_bucket(row):
        raw = str(row["started_at"] or "")
        try:
            hour = datetime.fromisoformat(raw.replace("Z", "+00:00")).hour
        except Exception:
            return ""
        if hour < 6:
            return "Overnight (00–05)"
        if hour < 12:
            return "Morning (06–11)"
        if hour < 18:
            return "Afternoon (12–17)"
        return "Evening (18–23)"

    time_analysis = _group_sessions(sessions, time_bucket)

    latest_duration = float(sessions[0]["duration_min"] or 0) if sessions else 0.0
    fatigue = {
        "active": latest_duration >= 60,
        "level": "strong" if latest_duration >= 90 else ("caution" if latest_duration >= 60 else "clear"),
        "durationMin": latest_duration,
        "message": (
            "Latest recorded session is long enough to justify a break. This is a behavioral safeguard, not a medical assessment."
            if latest_duration >= 60
            else "No duration-based fatigue flag from the latest recorded session."
        ),
    }

    prefs = load_preferences(con, user_id)
    pause_active = False
    if prefs["pause_until"]:
        try:
            pause_active = datetime.fromisoformat(prefs["pause_until"].replace("Z", "+00:00")) > datetime.now(timezone.utc)
        except Exception:
            pause_active = False
    pause = {
        "active": pause_active,
        "until": prefs["pause_until"],
        "message": "Session tools are paused by your responsible-play control." if pause_active else "No responsible-play pause is active.",
    }

    goals = []
    for row in con.execute(
        """SELECT id,goal_type,target,title,status,created_at,updated_at
           FROM return_goals WHERE user_id=? ORDER BY created_at DESC""",
        (user_id,),
    ).fetchall():
        current = _goal_current(con, user_id, row["goal_type"])
        target = max(1, int(row["target"] or 1))
        goals.append({
            "id": row["id"],
            "goalType": row["goal_type"],
            "title": row["title"],
            "status": row["status"],
            "current": current,
            "target": target,
            "progress": round(min(1.0, current / target), 4),
        })

    review_count = _goal_current(con, user_id, "tip_reviews")
    note_count = _goal_current(con, user_id, "reflection_notes")
    platforms = {str(r["platform"]) for r in sessions if r["platform"]}
    achievements = [
        {"id": "evidence-reviewer", "title": "Evidence Reviewer", "earned": review_count >= 3, "why": "Rate 3 coaching tips for usefulness."},
        {"id": "cross-platform", "title": "Cross-platform Comparator", "earned": len(platforms) >= 2, "why": "Record evidence on at least 2 platforms."},
        {"id": "reflection-logger", "title": "Reflection Logger", "earned": note_count >= 3, "why": "Write 3 reflection notes."},
        {"id": "safety-planner", "title": "Safety Planner", "earned": bool(prefs["pause_until"]), "why": "Use the responsible-play pause control at least once."},
    ]
    missions = [
        {"id": "rate-tip", "title": "Review one coaching tip", "done": review_count > 0, "featureId": "R006"},
        {"id": "reflect", "title": "Write one evidence reflection", "done": note_count > 0, "featureId": "R033"},
        {"id": "compare", "title": "Review your personal best without treating it as a prediction", "done": best is not None, "featureId": "R009"},
    ]

    media = []
    media_tags = {}
    for row in con.execute(
        """SELECT id,kind,file_name,mime_type,byte_size,review_note,tags_json,created_at,updated_at
           FROM return_media WHERE user_id=? ORDER BY created_at DESC LIMIT 100""",
        (user_id,),
    ).fetchall():
        tags = _loads(row["tags_json"], [])
        if not isinstance(tags, list):
            tags = []
        for tag in tags:
            media_tags[str(tag)] = media_tags.get(str(tag), 0) + 1
        media.append({
            "id": row["id"],
            "kind": row["kind"],
            "fileName": row["file_name"],
            "mimeType": row["mime_type"],
            "byteSize": row["byte_size"],
            "reviewNote": row["review_note"],
            "tags": tags,
            "createdAt": row["created_at"],
            "url": f"/api/return/media?id={row['id']}",
        })

    notes = []
    for row in con.execute(
        """SELECT id,note_type,body,tags_json,created_at FROM return_notes
           WHERE user_id=? ORDER BY created_at DESC LIMIT 100""",
        (user_id,),
    ).fetchall():
        tags = _loads(row["tags_json"], [])
        if not isinstance(tags, list):
            tags = []
        for tag in tags:
            media_tags[str(tag)] = media_tags.get(str(tag), 0) + 1
        notes.append({"id": row["id"], "noteType": row["note_type"], "body": row["body"], "tags": tags, "createdAt": row["created_at"]})

    saved_views = []
    for row in con.execute(
        """SELECT id,title,config_json,created_at,updated_at FROM return_saved_views
           WHERE user_id=? ORDER BY created_at DESC LIMIT 50""",
        (user_id,),
    ).fetchall():
        config = _loads(row["config_json"], {})
        saved_views.append({"id": row["id"], "title": row["title"], "config": config if isinstance(config, dict) else {}, "createdAt": row["created_at"]})

    return {
        "schema": "egm.return-workspace.v1",
        "personalBest": best,
        "targetEfficiency": target_eff,
        "weaponEfficiency": weapon_eff,
        "denominationComparison": denom_eff,
        "timeAnalysis": time_analysis,
        "fatigueWarning": fatigue,
        "pause": pause,
        "notificationControls": prefs,
        "goals": goals,
        "goalTypes": [{"id": k, **v} for k, v in SAFE_GOAL_TYPES.items()],
        "achievements": achievements,
        "missions": missions,
        "coachInbox": [
            {
                "tipId": row["id"],
                "title": row["title"],
                "body": row["body"],
                "confidence": row["confidence"],
                "createdAt": row["created_at"],
                "rating": row["rating"],
                "ratingNote": row["rating_note"],
            }
            for row in tips
        ],
        "media": media,
        "notes": notes,
        "smartTags": [{"tag": k, "count": v} for k, v in sorted(media_tags.items(), key=lambda x: (-x[1], x[0]))],
        "savedViews": saved_views,
        "safetyBoundary": "All comparisons describe user-authorized recorded evidence. Personal bests, efficiency summaries, and time patterns are historical descriptions, not predictions of future random outcomes or profit.",
    }
