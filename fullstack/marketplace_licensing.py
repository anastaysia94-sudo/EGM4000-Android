"""C008 A082 creator/coach marketplace fee + A083 white-label licensing.

Marketplace requests and white-label licenses have real persisted lifecycle and fee/access
controls. Manual owner actions may record complimentary or external-unverified states,
but provider-verified payment/access is reserved for A095 signed reconciliation.
"""
from __future__ import annotations

from datetime import datetime, timezone
import ipaddress
import secrets
from urllib.parse import urlparse

from storage import rowdict, rowsdict, scalar

LISTING_STATUSES={"draft","active","archived"}
ORDER_STATUSES={"requested","accepted","in_progress","delivered","cancelled"}
PAYMENT_STATUSES={"external_unverified","not_required","provider_verified"}
LICENSE_STATUSES={"active","revoked"}
MANUAL_LICENSE_SOURCES={"complimentary","external_unverified"}


def _now():return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
def _text(v,n=1000):return str(v or "").replace("\x00","").strip()[:n]


def _https_url(v):
    v=_text(v,1200)
    if not v:return ""
    p=urlparse(v)
    if p.scheme.lower()!="https" or not p.hostname or p.username or p.password:raise ValueError("https_url_required")
    host=p.hostname.lower().rstrip(".")
    if host in {"localhost","localhost.localdomain"} or host.endswith(".local"):raise ValueError("private_url_not_allowed")
    try:
        ip=ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:raise ValueError("private_url_not_allowed")
    except ValueError as exc:
        if str(exc)=="private_url_not_allowed":raise
    return v


def migrate_marketplace_licensing(con):
    stmts=[
        """CREATE TABLE IF NOT EXISTS coach_marketplace_listings(
            id TEXT PRIMARY KEY,coach_user_id INTEGER NOT NULL,title TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',
            service_label TEXT NOT NULL DEFAULT '',price_cents INTEGER NOT NULL,platform_fee_bps INTEGER NOT NULL DEFAULT 1500,
            status TEXT NOT NULL DEFAULT 'draft',created_at TEXT NOT NULL,updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS coach_marketplace_orders(
            id TEXT PRIMARY KEY,listing_id TEXT NOT NULL,buyer_user_id INTEGER NOT NULL,request_note TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'requested',payment_status TEXT NOT NULL DEFAULT 'external_unverified',
            gross_cents INTEGER NOT NULL,platform_fee_cents INTEGER NOT NULL,creator_net_cents INTEGER NOT NULL,
            provider_ref TEXT NOT NULL DEFAULT '',delivery_note TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS white_label_licenses(
            id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'active',source TEXT NOT NULL,source_ref TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS white_label_profiles(
            user_id INTEGER PRIMARY KEY,brand_name TEXT NOT NULL,support_label TEXT NOT NULL DEFAULT '',logo_url TEXT NOT NULL DEFAULT '',
            accent_label TEXT NOT NULL DEFAULT '',footer_text TEXT NOT NULL DEFAULT '',updated_at TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_market_listings_status ON coach_marketplace_listings(status,updated_at)",
        "CREATE INDEX IF NOT EXISTS idx_market_orders_buyer ON coach_marketplace_orders(buyer_user_id,created_at)",
        "CREATE INDEX IF NOT EXISTS idx_market_orders_listing ON coach_marketplace_orders(listing_id,created_at)",
        "CREATE INDEX IF NOT EXISTS idx_white_label_user ON white_label_licenses(user_id,updated_at)",
    ]
    for s in stmts:con.execute(s)
    con.commit()


def _listing_dict(row):
    d=rowdict(row);return {"id":d["id"],"coachUserId":int(d["coach_user_id"]),"coachName":d.get("coach_name","") if isinstance(d,dict) else "","title":d["title"],"description":d["description"],"serviceLabel":d["service_label"],"priceCents":int(d["price_cents"]),"platformFeeBps":int(d["platform_fee_bps"]),"platformFeePercent":round(int(d["platform_fee_bps"])/100,2),"status":d["status"],"createdAt":d["created_at"],"updatedAt":d["updated_at"]}


def save_listing(con,coach_user_id,payload):
    if not con.execute("SELECT id FROM users WHERE id=? AND status='active'",(int(coach_user_id),)).fetchone():raise ValueError("coach_user_not_found")
    lid=_text(payload.get("id"),80) or f"ml_{secrets.token_hex(10)}";title=_text(payload.get("title"),180);description=_text(payload.get("description"),3000);label=_text(payload.get("service_label"),120);status=_text(payload.get("status") or "draft",20).lower()
    if not title:raise ValueError("marketplace_title_required")
    if status not in LISTING_STATUSES:raise ValueError("invalid_marketplace_listing_status")
    price=int(payload.get("price_cents") or 0);fee=int(payload.get("platform_fee_bps") or 1500)
    if price<100 or price>10_000_000:raise ValueError("invalid_marketplace_price")
    if fee<0 or fee>5000:raise ValueError("invalid_marketplace_fee")
    stamp=_now();existing=con.execute("SELECT id,coach_user_id FROM coach_marketplace_listings WHERE id=?",(lid,)).fetchone()
    if existing and int(existing["coach_user_id"])!=int(coach_user_id):raise PermissionError("listing_owner_required")
    if existing:con.execute("UPDATE coach_marketplace_listings SET title=?,description=?,service_label=?,price_cents=?,platform_fee_bps=?,status=?,updated_at=? WHERE id=?",(title,description,label,price,fee,status,stamp,lid))
    else:con.execute("INSERT INTO coach_marketplace_listings(id,coach_user_id,title,description,service_label,price_cents,platform_fee_bps,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",(lid,int(coach_user_id),title,description,label,price,fee,status,stamp,stamp))
    con.commit();row=con.execute("SELECT l.*,u.display_name coach_name FROM coach_marketplace_listings l JOIN users u ON u.id=l.coach_user_id WHERE l.id=?",(lid,)).fetchone();return _listing_dict(row)


def marketplace_catalog(con):
    rows=con.execute("SELECT l.*,u.display_name coach_name FROM coach_marketplace_listings l JOIN users u ON u.id=l.coach_user_id WHERE l.status='active' ORDER BY l.updated_at DESC,l.id DESC").fetchall()
    return {"schema":"egm.coach-marketplace.v1","listings":[_listing_dict(r) for r in rows],"feeBoundary":"Displayed platform fees are contractual ledger amounts. A request or owner status change does not prove payment; provider verification is handled only by signed billing reconciliation.","safetyBoundary":"Coach services may analyze authorized recorded evidence but must not promise winnings, hidden-state access, random-outcome certainty, or balance manipulation."}


def create_marketplace_order(con,buyer_user_id,listing_id,note=""):
    listing=con.execute("SELECT * FROM coach_marketplace_listings WHERE id=? AND status='active'",(_text(listing_id,80),)).fetchone()
    if not listing:raise ValueError("marketplace_listing_not_available")
    if int(listing["coach_user_id"])==int(buyer_user_id):raise ValueError("cannot_order_own_listing")
    if con.execute("SELECT id FROM coach_marketplace_orders WHERE listing_id=? AND buyer_user_id=? AND status IN ('requested','accepted','in_progress')",(listing["id"],int(buyer_user_id))).fetchone():raise ValueError("active_marketplace_order_exists")
    gross=int(listing["price_cents"]);fee=(gross*int(listing["platform_fee_bps"])+5000)//10000;net=gross-fee;oid=f"mo_{secrets.token_hex(10)}";stamp=_now()
    con.execute("INSERT INTO coach_marketplace_orders(id,listing_id,buyer_user_id,request_note,status,payment_status,gross_cents,platform_fee_cents,creator_net_cents,provider_ref,delivery_note,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(oid,listing["id"],int(buyer_user_id),_text(note,3000),"requested","external_unverified",gross,fee,net,"","",stamp,stamp));con.commit();return get_marketplace_order(con,oid,buyer_user_id=buyer_user_id)


def _order_dict(row):
    d=rowdict(row);return {"id":d["id"],"listingId":d["listing_id"],"buyerUserId":int(d["buyer_user_id"]),"coachUserId":int(d["coach_user_id"]),"title":d["title"],"coachName":d["coach_name"],"buyerName":d["buyer_name"],"requestNote":d["request_note"],"status":d["status"],"paymentStatus":d["payment_status"],"grossCents":int(d["gross_cents"]),"platformFeeCents":int(d["platform_fee_cents"]),"creatorNetCents":int(d["creator_net_cents"]),"providerRef":d["provider_ref"],"deliveryNote":d["delivery_note"],"createdAt":d["created_at"],"updatedAt":d["updated_at"]}


def _order_join_sql():return """SELECT o.*,l.coach_user_id,l.title,cu.display_name coach_name,bu.display_name buyer_name FROM coach_marketplace_orders o JOIN coach_marketplace_listings l ON l.id=o.listing_id JOIN users cu ON cu.id=l.coach_user_id JOIN users bu ON bu.id=o.buyer_user_id"""

def get_marketplace_order(con,order_id,buyer_user_id=None,coach_user_id=None):
    sql=_order_join_sql()+" WHERE o.id=?";params=[_text(order_id,80)]
    if buyer_user_id is not None:sql+=" AND o.buyer_user_id=?";params.append(int(buyer_user_id))
    if coach_user_id is not None:sql+=" AND l.coach_user_id=?";params.append(int(coach_user_id))
    row=con.execute(sql,tuple(params)).fetchone();return _order_dict(row) if row else None


def my_marketplace(con,user_id):
    buys=con.execute(_order_join_sql()+" WHERE o.buyer_user_id=? ORDER BY o.created_at DESC",(int(user_id),)).fetchall();sells=con.execute(_order_join_sql()+" WHERE l.coach_user_id=? ORDER BY o.created_at DESC",(int(user_id),)).fetchall();mine=con.execute("SELECT l.*,u.display_name coach_name FROM coach_marketplace_listings l JOIN users u ON u.id=l.coach_user_id WHERE l.coach_user_id=? ORDER BY l.updated_at DESC",(int(user_id),)).fetchall();return {"schema":"egm.my-coach-marketplace.v1","listings":[_listing_dict(r) for r in mine],"purchases":[_order_dict(r) for r in buys],"sales":[_order_dict(r) for r in sells],"boundary":"Payment status stays external_unverified until signed A095 provider reconciliation confirms it."}


def update_marketplace_order(con,coach_user_id,order_id,status,delivery_note=""):
    status=_text(status,30).lower()
    if status not in ORDER_STATUSES:raise ValueError("invalid_marketplace_order_status")
    order=get_marketplace_order(con,order_id,coach_user_id=coach_user_id)
    if not order:raise ValueError("marketplace_order_not_found")
    delivery=_text(delivery_note,6000)
    if status=="delivered" and not delivery:raise ValueError("marketplace_delivery_note_required")
    con.execute("UPDATE coach_marketplace_orders SET status=?,delivery_note=?,updated_at=? WHERE id=?",(status,delivery,_now(),order["id"]));con.commit();return get_marketplace_order(con,order["id"])


def provider_verify_marketplace_order(con,order_id,provider_ref):
    order=get_marketplace_order(con,order_id)
    if not order:raise ValueError("marketplace_order_not_found")
    con.execute("UPDATE coach_marketplace_orders SET payment_status='provider_verified',provider_ref=?,updated_at=? WHERE id=?",(_text(provider_ref,120),_now(),order["id"]));con.commit();return get_marketplace_order(con,order["id"])


def provider_cancel_marketplace_payment(con,order_id,provider_ref):
    order=get_marketplace_order(con,order_id)
    if not order:raise ValueError("marketplace_order_not_found")
    con.execute("UPDATE coach_marketplace_orders SET payment_status='external_unverified',provider_ref=?,updated_at=? WHERE id=?",(_text(provider_ref,120),_now(),order["id"]));con.commit()


def marketplace_admin(con):
    orders=con.execute(_order_join_sql()+" ORDER BY o.updated_at DESC").fetchall();fee_due=sum(int(r["platform_fee_cents"]) for r in orders if r["payment_status"]=="provider_verified" and r["status"]!="cancelled");return {"schema":"egm.admin.coach-marketplace.v1","orders":[_order_dict(r) for r in orders],"summary":{"orders":len(orders),"providerVerified":sum(1 for r in orders if r["payment_status"]=="provider_verified"),"verifiedPlatformFeeCents":fee_due},"boundary":"Platform-fee totals count only provider-verified orders. External-unverified orders are never treated as collected revenue."}


def white_label_status(con,user_id):
    row=con.execute("SELECT * FROM white_label_licenses WHERE user_id=? ORDER BY updated_at DESC LIMIT 1",(int(user_id),)).fetchone();profile=con.execute("SELECT * FROM white_label_profiles WHERE user_id=?",(int(user_id),)).fetchone()
    lic={"active":False,"source":None,"sourceRef":"","status":"not_granted","updatedAt":None}
    if row:
        d=rowdict(row);lic={"id":d["id"],"active":d["status"]=="active","source":d["source"],"sourceRef":d["source_ref"],"status":d["status"],"note":d["note"],"updatedAt":d["updated_at"]}
    return {"schema":"egm.white-label-license.v1","license":lic,"profile":dict(rowdict(profile)) if profile else None,"boundary":"White-label access changes presentation and licensing rights only. Manual grants are not provider payment verification."}


def grant_white_label(con,user_id,source="complimentary",note="",source_ref=""):
    source=_text(source,40)
    if source not in MANUAL_LICENSE_SOURCES:raise ValueError("unsupported_manual_license_source")
    if not con.execute("SELECT id FROM users WHERE id=? AND status='active'",(int(user_id),)).fetchone():raise ValueError("license_user_not_found")
    stamp=_now();existing=con.execute("SELECT id FROM white_label_licenses WHERE user_id=? ORDER BY updated_at DESC LIMIT 1",(int(user_id),)).fetchone()
    if existing:
        lid=existing["id"];con.execute("UPDATE white_label_licenses SET status='active',source=?,source_ref=?,note=?,updated_at=? WHERE id=?",(source,_text(source_ref,120),_text(note,2000),stamp,lid))
    else:
        lid=f"wl_{secrets.token_hex(10)}";con.execute("INSERT INTO white_label_licenses(id,user_id,status,source,source_ref,note,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",(lid,int(user_id),"active",source,_text(source_ref,120),_text(note,2000),stamp,stamp))
    con.commit();return white_label_status(con,user_id)


def provider_verify_white_label(con,user_id,provider_ref):
    if not con.execute("SELECT id FROM users WHERE id=? AND status='active'",(int(user_id),)).fetchone():raise ValueError("license_user_not_found")
    stamp=_now();existing=con.execute("SELECT id FROM white_label_licenses WHERE user_id=? ORDER BY updated_at DESC LIMIT 1",(int(user_id),)).fetchone()
    if existing:
        lid=existing["id"];con.execute("UPDATE white_label_licenses SET status='active',source='provider_verified',source_ref=?,note='Verified provider event',updated_at=? WHERE id=?",(_text(provider_ref,120),stamp,lid))
    else:
        lid=f"wl_{secrets.token_hex(10)}";con.execute("INSERT INTO white_label_licenses(id,user_id,status,source,source_ref,note,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",(lid,int(user_id),"active","provider_verified",_text(provider_ref,120),"Verified provider event",stamp,stamp))
    con.commit();return white_label_status(con,user_id)


def revoke_white_label(con,user_id,note=""):
    row=con.execute("SELECT id FROM white_label_licenses WHERE user_id=? ORDER BY updated_at DESC LIMIT 1",(int(user_id),)).fetchone()
    if not row:raise ValueError("white_label_license_not_found")
    con.execute("UPDATE white_label_licenses SET status='revoked',note=?,updated_at=? WHERE id=?",(_text(note,2000),_now(),row["id"]));con.commit()


def save_white_label_profile(con,user_id,payload):
    st=white_label_status(con,user_id)
    if not st["license"]["active"]:raise PermissionError("white_label_license_required")
    brand=_text(payload.get("brand_name"),180)
    if not brand:raise ValueError("white_label_brand_required")
    logo=_https_url(payload.get("logo_url"));support=_text(payload.get("support_label"),180);accent=_text(payload.get("accent_label"),80);footer=_text(payload.get("footer_text"),500);stamp=_now();existing=con.execute("SELECT user_id FROM white_label_profiles WHERE user_id=?",(int(user_id),)).fetchone()
    if existing:con.execute("UPDATE white_label_profiles SET brand_name=?,support_label=?,logo_url=?,accent_label=?,footer_text=?,updated_at=? WHERE user_id=?",(brand,support,logo,accent,footer,stamp,int(user_id)))
    else:con.execute("INSERT INTO white_label_profiles(user_id,brand_name,support_label,logo_url,accent_label,footer_text,updated_at) VALUES(?,?,?,?,?,?,?)",(int(user_id),brand,support,logo,accent,footer,stamp))
    con.commit();return white_label_status(con,user_id)


def white_label_preview(con,user_id):
    st=white_label_status(con,user_id)
    if not st["license"]["active"]:raise PermissionError("white_label_license_required")
    p=st["profile"] or {"brand_name":"Licensed EGM4000 Experience","support_label":"","logo_url":"","accent_label":"","footer_text":""}
    return {"schema":"egm.white-label-preview.v1","brandName":p.get("brand_name",""),"supportLabel":p.get("support_label",""),"logoUrl":p.get("logo_url",""),"accentLabel":p.get("accent_label",""),"footerText":p.get("footer_text",""),"poweredBy":"EGM4000 / SmartPickShop Holdings","boundary":"White-label presentation does not alter evidence provenance, randomness, safety disclosures, or provider boundaries."}


def white_label_admin(con):
    rows=con.execute("""SELECT l.*,u.username,u.display_name,p.brand_name FROM white_label_licenses l JOIN users u ON u.id=l.user_id LEFT JOIN white_label_profiles p ON p.user_id=l.user_id ORDER BY l.updated_at DESC""").fetchall();return {"schema":"egm.admin.white-label.v1","licenses":[dict(rowdict(r)) for r in rows],"boundary":"provider_verified licenses must originate from signed A095 reconciliation, never a manual owner toggle."}
