"""C016 confidence-calibrated multi-session coaching trends.

This module rolls completed C014 behavior/evidence-quality comparisons into
multi-session patterns. It deliberately excludes random credit/payout outcomes
from the trend score and never treats correlation as causation.
"""
from __future__ import annotations

from collections import defaultdict
from storage import rowdict, rowsdict, scalar

SCHEMA = "egm.coaching-trends.v1"
OWNER_SCHEMA = "egm.admin.coaching-trend-overview.v1"
MIN_COMPLETED = 3
MIN_WEIGHT = 1.20
DIRECTION_THRESHOLD = 0.25
RESULT_SCORE = {"improved": 1.0, "worsened": -1.0, "unchanged": 0.0}
METRIC_LABELS = {
    "shots_per_min": "shot pace",
    "max_drawdown": "recorded drawdown",
    "breaks": "recorded breaks",
    "evidence_completeness": "evidence completeness",
}
BOUNDARY = (
    "Multi-session trends summarize completed behavior/evidence-quality comparisons only. "
    "They are observed associations, not causal proof, and they do not use random credit, "
    "payout, profit, or hidden-state outcomes as evidence that coaching worked."
)


def _clamp(value, low=0.0, high=1.0):
    try:
        return max(low, min(high, float(value)))
    except Exception:
        return low


def _weight(row):
    confidence = _clamp(row.get("confidence"))
    base_n = max(0, int(row.get("baseline_sample_size") or 0))
    follow_n = max(0, int(row.get("followup_sample_size") or 0))
    comparable_n = min(base_n, follow_n)
    maturity = min(1.0, comparable_n / 20.0)
    return confidence * (0.50 + (0.50 * maturity))


def _classify(count, total_weight, balance):
    if count < MIN_COMPLETED or total_weight < MIN_WEIGHT:
        return "insufficient_evidence"
    if balance >= DIRECTION_THRESHOLD:
        return "improving_pattern"
    if balance <= -DIRECTION_THRESHOLD:
        return "worsening_pattern"
    return "mixed_or_stable"


def _label(classification):
    return {
        "improving_pattern": "Improving pattern",
        "worsening_pattern": "Worsening pattern",
        "mixed_or_stable": "Mixed / stable pattern",
        "insufficient_evidence": "Insufficient evidence",
    }.get(classification, classification)


def _group(rows):
    grouped = defaultdict(list)
    for row in rows:
        result = row.get("result")
        metric = row.get("target_metric")
        platform = row.get("platform") or "generic"
        if result not in RESULT_SCORE or metric not in METRIC_LABELS:
            continue
        grouped[(platform, metric)].append(row)

    output = []
    for (platform, metric), items in sorted(grouped.items()):
        weights = [_weight(x) for x in items]
        total_weight = sum(weights)
        weighted_score = sum(RESULT_SCORE[x["result"]] * w for x, w in zip(items, weights))
        balance = (weighted_score / total_weight) if total_weight > 0 else 0.0
        weighted_conf = (
            sum(_clamp(x.get("confidence")) * w for x, w in zip(items, weights)) / total_weight
            if total_weight > 0 else 0.0
        )
        maturity = min(1.0, len(items) / 5.0)
        calibrated = round(weighted_conf * (0.55 + 0.45 * maturity), 3)
        counts = {k: sum(1 for x in items if x.get("result") == k) for k in RESULT_SCORE}
        classification = _classify(len(items), total_weight, balance)
        sessions = sorted({int(v) for x in items for v in (x.get("baseline_live_session_id"), x.get("followup_live_session_id")) if v})
        output.append({
            "platform": platform,
            "targetMetric": metric,
            "metricLabel": METRIC_LABELS[metric],
            "completedComparisons": len(items),
            "results": counts,
            "evidenceWeight": round(total_weight, 3),
            "evidenceBalance": round(balance, 3),
            "confidence": calibrated,
            "classification": classification,
            "classificationLabel": _label(classification),
            "sessionCount": len(sessions),
            "sessionIds": sessions[-20:],
            "uncertainty": (
                "At least three comparable completed C014 comparisons are required before a directional pattern is shown."
                if classification == "insufficient_evidence"
                else "Pattern direction reflects repeated recorded comparisons; it remains associative rather than causal."
            ),
        })
    return output


def user_trends(con, user_id: int, platform: str | None = None):
    params = [int(user_id)]
    where = "WHERE user_id=? AND status='completed'"
    if platform:
        where += " AND platform=?"
        params.append(str(platform))
    rows = rowsdict(con.execute(
        f"""SELECT id,platform,target_metric,result,confidence,baseline_sample_size,followup_sample_size,
        baseline_live_session_id,followup_live_session_id,updated_at
        FROM coaching_experiments {where} ORDER BY updated_at,id""",
        tuple(params),
    ).fetchall())
    groups = _group(rows)
    return {
        "schema": SCHEMA,
        "userId": int(user_id),
        "completedComparisons": len(rows),
        "groups": groups,
        "summary": {
            "directionalGroups": sum(1 for g in groups if g["classification"] in ("improving_pattern", "worsening_pattern")),
            "mixedOrStableGroups": sum(1 for g in groups if g["classification"] == "mixed_or_stable"),
            "insufficientGroups": sum(1 for g in groups if g["classification"] == "insufficient_evidence"),
        },
        "boundary": BOUNDARY,
    }


def owner_overview(con):
    rows = rowsdict(con.execute(
        """SELECT e.id,e.platform,e.target_metric,e.result,e.confidence,e.baseline_sample_size,e.followup_sample_size,
        e.baseline_live_session_id,e.followup_live_session_id,e.updated_at
        FROM coaching_experiments e JOIN users u ON u.id=e.user_id
        WHERE e.status='completed' AND u.status='active' AND u.is_synthetic=0
        ORDER BY e.updated_at,e.id"""
    ).fetchall())
    groups = _group(rows)
    eligible_users = int(scalar(con, "SELECT COUNT(*) FROM users WHERE status='active' AND is_synthetic=0") or 0)
    measured_users = int(scalar(con, """SELECT COUNT(DISTINCT e.user_id) FROM coaching_experiments e JOIN users u ON u.id=e.user_id
        WHERE e.status='completed' AND u.status='active' AND u.is_synthetic=0""") or 0)
    return {
        "schema": OWNER_SCHEMA,
        "eligibleRealUsers": eligible_users,
        "measuredRealUsers": measured_users,
        "completedComparisons": len(rows),
        "groups": groups,
        "boundary": BOUNDARY + " Synthetic seed accounts are excluded from owner adoption/trend counts.",
    }


def migrate_coaching_trends(con):
    try:
        row = con.execute("SELECT id FROM checklist WHERE id='C016'").fetchone()
        note = "Implemented: confidence-calibrated multi-session C014 trends using behavior/evidence-quality metrics only; random outcomes excluded."
        if row:
            con.execute("UPDATE checklist SET title=?,done=1,notes=? WHERE id='C016'", ("Multi-session coaching effectiveness trends", note))
        else:
            con.execute("INSERT INTO checklist(id,title,done,notes) VALUES(?,?,?,?)", ("C016", "Multi-session coaching effectiveness trends", 1, note))
        con.commit()
    except Exception:
        con.rollback()
