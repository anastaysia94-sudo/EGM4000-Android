"""Provider-independent C008 monetization assets.

These capabilities intentionally stop short of payment processing. They implement
trackable outbound referrals, disclosed sponsored educational placements, course
upsells, and promotional bundles without storing provider credentials or claiming
that a billing integration exists.
"""
from __future__ import annotations

from datetime import datetime, timezone
import ipaddress
import re
import secrets
from urllib.parse import urlparse

from storage import scalar

KIND_CAPABILITY = {
    "partner_referral": "A079",
    "sponsored_education": "A081",
    "hardware_referral": "A090",
    "course_upsell": "A091",
    "promo_bundle": "A093",
}
CAPABILITY_KIND = {v: k for k, v in KIND_CAPABILITY.items()}

UNSAFE_CLAIM_RE = re.compile(
    r"\b(guaranteed\s+(?:profit|profits|win|wins|winnings|income|return)|"
    r"risk[- ]?free\s+(?:profit|win|winnings)|never\s+lose)\b",
    re.I,
)
SLUG_RE = re.compile(r"[^a-z0-9]+")


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _text(value, limit):
    return str(value or "").replace("\x00", "").strip()[:limit]


def migrate_monetization_assets(con):
    con.execute(
        """CREATE TABLE IF NOT EXISTS monetization_assets(
            id TEXT PRIMARY KEY,
            capability_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL DEFAULT '',
            price_label TEXT NOT NULL DEFAULT '',
            destination_url TEXT NOT NULL,
            disclosure TEXT NOT NULL DEFAULT '',
            active INTEGER NOT NULL DEFAULT 0,
            updated_by INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    con.execute(
        """CREATE TABLE IF NOT EXISTS monetization_asset_events(
            event_id TEXT PRIMARY KEY,
            asset_id TEXT NOT NULL,
            capability_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_monetization_asset_events_asset ON monetization_asset_events(asset_id,created_at)")
    con.commit()


def validate_destination(value):
    url = _text(value, 1200)
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValueError("https_destination_required")
    if parsed.username or parsed.password:
        raise ValueError("destination_credentials_not_allowed")
    host = parsed.hostname.lower().rstrip(".")
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise ValueError("private_destination_not_allowed")
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("private_destination_not_allowed")
    except ValueError as exc:
        if str(exc) == "private_destination_not_allowed":
            raise
        # A normal DNS hostname is allowed; deployment/network policy remains the
        # final authority for whether a destination is reachable.
        pass
    return url


def validate_claims(*values):
    text = " ".join(_text(v, 4000) for v in values)
    if UNSAFE_CLAIM_RE.search(text):
        raise ValueError("unsafe_guarantee_claim")


def _slug(value):
    candidate = SLUG_RE.sub("-", _text(value, 100).lower()).strip("-")[:64]
    return candidate or "offer"


def _unique_slug(con, desired, asset_id=None):
    base = _slug(desired)
    candidate = base
    for _ in range(8):
        row = con.execute("SELECT id FROM monetization_assets WHERE slug=?", (candidate,)).fetchone()
        if not row or str(row["id"]) == str(asset_id or ""):
            return candidate
        candidate = f"{base[:51]}-{secrets.token_hex(4)}"
    raise ValueError("slug_unavailable")


def save_asset(con, owner_id, payload):
    if not isinstance(payload, dict):
        raise ValueError("invalid_asset_payload")
    kind = _text(payload.get("kind"), 40)
    capability_id = KIND_CAPABILITY.get(kind)
    if not capability_id:
        raise ValueError("unsupported_asset_kind")
    asset_id = _text(payload.get("id"), 80) or f"ma_{secrets.token_hex(12)}"
    title = _text(payload.get("title"), 180)
    body = _text(payload.get("body"), 3000)
    price_label = _text(payload.get("price_label"), 120)
    if not title:
        raise ValueError("asset_title_required")
    destination = validate_destination(payload.get("destination_url"))
    disclosure = _text(payload.get("disclosure"), 300)
    if kind == "sponsored_education" and not disclosure:
        disclosure = "Sponsored educational placement."
    validate_claims(title, body, price_label, disclosure)
    active = 1 if bool(payload.get("active")) else 0
    existing = con.execute("SELECT id,slug,created_at FROM monetization_assets WHERE id=?", (asset_id,)).fetchone()
    desired_slug = payload.get("slug") or (existing["slug"] if existing else title)
    slug = _unique_slug(con, desired_slug, asset_id)
    stamp = _now()
    if existing:
        con.execute(
            """UPDATE monetization_assets
               SET capability_id=?,kind=?,slug=?,title=?,body=?,price_label=?,destination_url=?,disclosure=?,active=?,updated_by=?,updated_at=?
               WHERE id=?""",
            (capability_id, kind, slug, title, body, price_label, destination, disclosure, active, owner_id, stamp, asset_id),
        )
    else:
        con.execute(
            """INSERT INTO monetization_assets(
                 id,capability_id,kind,slug,title,body,price_label,destination_url,disclosure,active,updated_by,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (asset_id, capability_id, kind, slug, title, body, price_label, destination, disclosure, active, owner_id, stamp, stamp),
        )
    con.commit()
    return get_asset(con, asset_id)


def archive_asset(con, asset_id, owner_id=None):
    asset_id = _text(asset_id, 80)
    row = con.execute("SELECT id FROM monetization_assets WHERE id=?", (asset_id,)).fetchone()
    if not row:
        raise ValueError("asset_not_found")
    con.execute(
        "UPDATE monetization_assets SET active=0,updated_by=?,updated_at=? WHERE id=?",
        (owner_id, _now(), asset_id),
    )
    con.commit()
    return get_asset(con, asset_id)


def _asset_dict(row, clicks=0):
    return {
        "id": row["id"],
        "capabilityId": row["capability_id"],
        "kind": row["kind"],
        "slug": row["slug"],
        "title": row["title"],
        "body": row["body"],
        "priceLabel": row["price_label"],
        "destinationUrl": row["destination_url"],
        "disclosure": row["disclosure"],
        "active": bool(row["active"]),
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
        "clicks": int(clicks or 0),
        "goUrl": f"/go/{row['slug']}",
    }


def get_asset(con, asset_id):
    row = con.execute("SELECT * FROM monetization_assets WHERE id=?", (_text(asset_id, 80),)).fetchone()
    if not row:
        return None
    clicks = scalar(con, "SELECT COUNT(*) FROM monetization_asset_events WHERE asset_id=? AND event_type='click'", (row["id"],)) or 0
    return _asset_dict(row, clicks)


def admin_assets(con):
    rows = con.execute("SELECT * FROM monetization_assets ORDER BY updated_at DESC,title ASC").fetchall()
    counts = {
        str(r["asset_id"]): int(r["n"] or 0)
        for r in con.execute(
            "SELECT asset_id,COUNT(*) n FROM monetization_asset_events WHERE event_type='click' GROUP BY asset_id"
        ).fetchall()
    }
    assets = [_asset_dict(row, counts.get(str(row["id"]), 0)) for row in rows]
    by_capability = {cap: {"assets": 0, "active": 0, "clicks": 0} for cap in CAPABILITY_KIND}
    for asset in assets:
        bucket = by_capability[asset["capabilityId"]]
        bucket["assets"] += 1
        bucket["active"] += 1 if asset["active"] else 0
        bucket["clicks"] += asset["clicks"]
    return {
        "schema": "egm.admin.monetization-assets.v1",
        "assets": assets,
        "capabilities": by_capability,
        "privacy": "Click measurement is aggregate. This ledger does not store raw IP addresses, browser fingerprints, or cross-site visitor identifiers.",
    }


def public_catalog(con):
    rows = con.execute("SELECT * FROM monetization_assets WHERE active=1 ORDER BY updated_at DESC,title ASC").fetchall()
    out = []
    for row in rows:
        item = _asset_dict(row, 0)
        # Public clients never need the raw destination because /go/<slug> is the
        # measured, server-validated handoff.
        item.pop("destinationUrl", None)
        item.pop("clicks", None)
        item["sponsored"] = row["kind"] == "sponsored_education"
        out.append(item)
    return {
        "schema": "egm.monetization-catalog.v1",
        "assets": out,
        "safety": "Commercial links are optional and must not be presented as evidence that gameplay will produce profit or predictable random outcomes.",
    }


def resolve_click(con, slug):
    row = con.execute("SELECT * FROM monetization_assets WHERE slug=? AND active=1", (_slug(slug),)).fetchone()
    if not row:
        return None
    con.execute(
        "INSERT INTO monetization_asset_events(event_id,asset_id,capability_id,event_type,created_at) VALUES(?,?,?,?,?)",
        (f"me_{secrets.token_hex(12)}", row["id"], row["capability_id"], "click", _now()),
    )
    con.commit()
    return _asset_dict(row, 0)
