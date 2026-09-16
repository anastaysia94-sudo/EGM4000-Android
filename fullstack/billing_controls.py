"""C008 billing/access controls for A072/A086/A088/A094/A095.

Manual owner actions may provision complimentary or externally-unverified access,
but only a correctly signed provider event may create provider-verified state.
The webhook verification secret is read from process environment and never stored.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
import secrets

from storage import rowdict, rowsdict, scalar
from commercial_suite import grant_subscription

A072="A072"; A086="A086"; A088="A088"
ADDON_FEATURES={A072,A086,A088}
MANUAL_SOURCES={"complimentary","external_unverified"}
PROVIDER_SOURCE="provider_verified"
COUPON_KINDS={"trial_plan","feature_trial","coaching_units","retention_trial","discount"}
PROVIDER_EVENT_TYPES={"plan_active","plan_cancelled","feature_active","feature_cancelled"}


def _now_dt(): return datetime.now(timezone.utc).replace(microsecond=0)
def _now(): return _now_dt().isoformat()
def _text(v,n=1000): return str(v or "").replace("\x00","").strip()[:n]

def _parse_time(v):
    if not v:return None
    try:
        dt=datetime.fromisoformat(str(v).replace("Z","+00:00"))
        if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:raise ValueError("invalid_timestamp")


def migrate_billing_controls(con):
    statements=[
        """CREATE TABLE IF NOT EXISTS billing_addon_access(
            id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,feature_id TEXT NOT NULL,status TEXT NOT NULL,
            source TEXT NOT NULL,source_ref TEXT NOT NULL DEFAULT '',limit_value INTEGER,retain_days INTEGER,
            note TEXT NOT NULL DEFAULT '',starts_at TEXT NOT NULL,ends_at TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS coaching_usage_events(
            id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,units INTEGER NOT NULL,context TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS retention_archives(
            id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,content_json TEXT NOT NULL,sha256 TEXT NOT NULL,row_count INTEGER NOT NULL,
            created_at TEXT NOT NULL,expires_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS commercial_coupons(
            code TEXT PRIMARY KEY,title TEXT NOT NULL,kind TEXT NOT NULL,target_plan_id TEXT,target_feature_id TEXT,
            trial_days INTEGER,unit_bonus INTEGER,retention_days INTEGER,discount_label TEXT NOT NULL DEFAULT '',
            max_redemptions INTEGER NOT NULL DEFAULT 1,active INTEGER NOT NULL DEFAULT 1,starts_at TEXT,ends_at TEXT,
            created_at TEXT NOT NULL,updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS commercial_coupon_redemptions(
            id TEXT PRIMARY KEY,code TEXT NOT NULL,user_id INTEGER NOT NULL,status TEXT NOT NULL,note TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,
            UNIQUE(code,user_id)
        )""",
        """CREATE TABLE IF NOT EXISTS billing_customer_links(
            id TEXT PRIMARY KEY,provider TEXT NOT NULL,customer_ref TEXT NOT NULL,user_id INTEGER NOT NULL,target_type TEXT NOT NULL,target_id TEXT NOT NULL,
            created_at TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(provider,customer_ref,target_type,target_id)
        )""",
        """CREATE TABLE IF NOT EXISTS billing_provider_events(
            provider_event_id TEXT PRIMARY KEY,provider TEXT NOT NULL,customer_ref TEXT NOT NULL,event_type TEXT NOT NULL,
            event_status TEXT NOT NULL,amount TEXT NOT NULL DEFAULT '',currency TEXT NOT NULL DEFAULT '',occurred_at TEXT NOT NULL,
            payload_hash TEXT NOT NULL,verification_status TEXT NOT NULL,reconciliation_status TEXT NOT NULL,note TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_billing_access_user ON billing_addon_access(user_id,feature_id,updated_at)",
        "CREATE INDEX IF NOT EXISTS idx_coaching_usage_user ON coaching_usage_events(user_id,created_at)",
        "CREATE INDEX IF NOT EXISTS idx_retention_archives_user ON retention_archives(user_id,created_at)",
        "CREATE INDEX IF NOT EXISTS idx_provider_events_customer ON billing_provider_events(provider,customer_ref,occurred_at)",
    ]
    for s in statements:con.execute(s)
    con.commit()


def _active_row(con,user_id,feature_id):
    if feature_id not in ADDON_FEATURES:return None
    stamp=_now()
    return con.execute("""SELECT * FROM billing_addon_access WHERE user_id=? AND feature_id=? AND status='active'
        AND (ends_at IS NULL OR ends_at='' OR ends_at>?) ORDER BY updated_at DESC LIMIT 1""",(int(user_id),feature_id,stamp)).fetchone()


def addon_status(con,user_id,feature_id):
    row=_active_row(con,user_id,feature_id)
    if not row:return {"featureId":feature_id,"active":False,"source":None,"endsAt":None}
    d=rowdict(row);out={"id":d["id"],"featureId":d["feature_id"],"active":True,"source":d["source"],"sourceRef":d["source_ref"],"limitValue":d["limit_value"],"retainDays":d["retain_days"],"endsAt":d["ends_at"],"note":d["note"],"updatedAt":d["updated_at"]}
    if feature_id==A072:
        used=int(scalar(con,"SELECT COALESCE(SUM(units),0) FROM coaching_usage_events WHERE user_id=?",(int(user_id),)) or 0)
        limit=int(d["limit_value"] or 0);out["usedUnits"]=used;out["remainingUnits"]=max(0,limit-used)
    return out


def grant_addon(con,user_id,feature_id,source="complimentary",limit_value=None,retain_days=None,note="",ends_at=None,source_ref=""):
    user_id=int(user_id);feature_id=_text(feature_id,20);source=_text(source,40)
    if feature_id not in ADDON_FEATURES:raise ValueError("unsupported_addon_feature")
    if source not in MANUAL_SOURCES:raise ValueError("unsupported_manual_addon_source")
    if not con.execute("SELECT id FROM users WHERE id=? AND status='active'",(user_id,)).fetchone():raise ValueError("addon_user_not_found")
    if feature_id==A072:
        limit_value=int(limit_value or 0)
        if limit_value<1 or limit_value>100000:raise ValueError("invalid_coaching_unit_limit")
    if feature_id==A088:
        retain_days=int(retain_days or 0)
        if retain_days<30 or retain_days>3650:raise ValueError("invalid_retention_days")
    stamp=_now();existing=con.execute("SELECT id FROM billing_addon_access WHERE user_id=? AND feature_id=? ORDER BY updated_at DESC LIMIT 1",(user_id,feature_id)).fetchone()
    if existing:
        aid=existing["id"];con.execute("UPDATE billing_addon_access SET status='active',source=?,source_ref=?,limit_value=?,retain_days=?,note=?,starts_at=?,ends_at=?,updated_at=? WHERE id=?",(source,_text(source_ref,200),limit_value,retain_days,_text(note,2000),stamp,ends_at,stamp,aid))
    else:
        aid=f"ba_{secrets.token_hex(10)}";con.execute("INSERT INTO billing_addon_access(id,user_id,feature_id,status,source,source_ref,limit_value,retain_days,note,starts_at,ends_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(aid,user_id,feature_id,"active",source,_text(source_ref,200),limit_value,retain_days,_text(note,2000),stamp,ends_at,stamp,stamp))
    con.commit();return addon_status(con,user_id,feature_id)


def revoke_addon(con,user_id,feature_id,note=""):
    row=con.execute("SELECT id FROM billing_addon_access WHERE user_id=? AND feature_id=? ORDER BY updated_at DESC LIMIT 1",(int(user_id),feature_id)).fetchone()
    if not row:raise ValueError("addon_access_not_found")
    con.execute("UPDATE billing_addon_access SET status='revoked',note=?,updated_at=? WHERE id=?",(_text(note,2000),_now(),row["id"]));con.commit()


def consume_coaching(con,user_id,context=""):
    st=addon_status(con,user_id,A072)
    if not st["active"]:raise PermissionError("usage_coaching_entitlement_required")
    if int(st.get("remainingUnits") or 0)<1:raise PermissionError("usage_coaching_limit_reached")
    rows=con.execute("SELECT id,session_id,created_at,title,body,evidence,confidence FROM tips WHERE user_id=? ORDER BY id DESC LIMIT 5",(int(user_id),)).fetchall()
    if not rows:raise ValueError("no_coaching_evidence_available")
    eid=f"cu_{secrets.token_hex(10)}";con.execute("INSERT INTO coaching_usage_events(id,user_id,units,context,created_at) VALUES(?,?,?,?,?)",(eid,int(user_id),1,_text(context,500),_now()));con.commit()
    return {"schema":"egm.usage-coaching.v1","usageEventId":eid,"unitCost":1,"status":addon_status(con,user_id,A072),"tips":rowsdict(rows),"boundary":"This metered coaching digest summarizes existing recorded evidence. Using more units does not improve random odds or guarantee a financial result."}


def retention_insights(con,user_id):
    if not addon_status(con,user_id,A086)["active"]:raise PermissionError("retention_insights_entitlement_required")
    dates=[]
    for r in con.execute("SELECT started_at FROM gameplay_sessions WHERE user_id=?",(int(user_id),)).fetchall():
        try:dates.append(_parse_time(r["started_at"]).date())
        except Exception:pass
    for r in con.execute("SELECT created_at FROM feature_usage_events WHERE user_id=?",(int(user_id),)).fetchall():
        try:dates.append(_parse_time(r["created_at"]).date())
        except Exception:pass
    unique=sorted(set(dates));gaps=[]
    for a,b in zip(unique,unique[1:]):gaps.append((b-a).days)
    cutoff=_now_dt().date()-timedelta(days=29)
    return {"schema":"egm.retention-insights.v1","activeDays":len(unique),"firstActiveDay":str(unique[0]) if unique else None,"lastActiveDay":str(unique[-1]) if unique else None,"activeDaysLast30":sum(1 for d in unique if d>=cutoff),"longestObservedGapDays":max(gaps) if gaps else 0,"meanObservedGapDays":round(sum(gaps)/len(gaps),2) if gaps else 0,"boundary":"Retention insights describe recorded return patterns only. They do not predict future behavior or gameplay outcomes."}


def _owned_archive_payload(con,user_id):
    sessions=rowsdict(con.execute("SELECT id,platform,started_at,duration_min,spend,payout,shots,hits,notes,source FROM gameplay_sessions WHERE user_id=? ORDER BY id",(int(user_id),)).fetchall())
    tips=rowsdict(con.execute("SELECT id,session_id,created_at,title,body,evidence,confidence FROM tips WHERE user_id=? ORDER BY id",(int(user_id),)).fetchall())
    if len(sessions)+len(tips)>20000:raise ValueError("retention_archive_too_large")
    return {"schema":"egm.retention-archive.v1","userId":int(user_id),"generatedAt":_now(),"sessions":sessions,"tips":tips,"boundary":"Owned historical evidence archive only; no credentials, auth tokens, visitor identifiers, or other users' rows."}


def create_retention_archive(con,user_id):
    st=addon_status(con,user_id,A088)
    if not st["active"]:raise PermissionError("premium_retention_entitlement_required")
    days=int(st.get("retainDays") or 0)
    payload=_owned_archive_payload(con,user_id);content=json.dumps(payload,separators=(",",":"),ensure_ascii=False);digest=hashlib.sha256(content.encode()).hexdigest();created=_now_dt();expires=created+timedelta(days=days);aid=f"ra_{secrets.token_hex(10)}"
    con.execute("INSERT INTO retention_archives(id,user_id,content_json,sha256,row_count,created_at,expires_at) VALUES(?,?,?,?,?,?,?)",(aid,int(user_id),content,digest,len(payload["sessions"])+len(payload["tips"]),created.isoformat(),expires.isoformat()));con.commit();return {"id":aid,"sha256":digest,"rowCount":len(payload["sessions"])+len(payload["tips"]),"createdAt":created.isoformat(),"expiresAt":expires.isoformat(),"retainDays":days}


def retention_archives(con,user_id,include_content=False):
    rows=con.execute("SELECT * FROM retention_archives WHERE user_id=? ORDER BY created_at DESC",(int(user_id),)).fetchall();out=[]
    for r in rows:
        d=rowdict(r);item={"id":d["id"],"sha256":d["sha256"],"rowCount":int(d["row_count"]),"createdAt":d["created_at"],"expiresAt":d["expires_at"]}
        if include_content:item["content"]=d["content_json"]
        out.append(item)
    return out


def get_retention_archive(con,user_id,archive_id):
    r=con.execute("SELECT * FROM retention_archives WHERE id=? AND user_id=?",(_text(archive_id,80),int(user_id))).fetchone()
    if not r:raise ValueError("retention_archive_not_found")
    d=rowdict(r);return {"id":d["id"],"sha256":d["sha256"],"rowCount":int(d["row_count"]),"createdAt":d["created_at"],"expiresAt":d["expires_at"],"content":d["content_json"]}


def prune_expired_archives(con,stamp=None):
    stamp=stamp or _now();count=int(scalar(con,"SELECT COUNT(*) FROM retention_archives WHERE expires_at<=?",(stamp,)) or 0);con.execute("DELETE FROM retention_archives WHERE expires_at<=?",(stamp,));con.commit();return count


def save_coupon(con,payload):
    code=_text(payload.get("code"),40).upper();title=_text(payload.get("title"),180);kind=_text(payload.get("kind"),30).lower()
    if not code or not all(c.isalnum() or c in {'-','_'} for c in code):raise ValueError("invalid_coupon_code")
    if not title:raise ValueError("coupon_title_required")
    if kind not in COUPON_KINDS:raise ValueError("invalid_coupon_kind")
    plan=_text(payload.get("target_plan_id"),80) or None;feature=_text(payload.get("target_feature_id"),20) or None
    if feature and feature not in ADDON_FEATURES:raise ValueError("unsupported_coupon_feature")
    trial=int(payload.get("trial_days") or 0) or None;units=int(payload.get("unit_bonus") or 0) or None;retention=int(payload.get("retention_days") or 0) or None;maximum=int(payload.get("max_redemptions") or 1)
    if maximum<1 or maximum>100000:raise ValueError("invalid_coupon_max_redemptions")
    if kind=='trial_plan' and (not plan or not trial or trial<1 or trial>365):raise ValueError("invalid_trial_plan_coupon")
    if kind=='feature_trial' and (not feature or not trial or trial<1 or trial>365):raise ValueError("invalid_feature_trial_coupon")
    if kind=='coaching_units' and (not units or units<1 or units>100000):raise ValueError("invalid_coaching_units_coupon")
    if kind=='retention_trial' and (not retention or retention<30 or retention>3650 or not trial or trial<1 or trial>365):raise ValueError("invalid_retention_trial_coupon")
    discount=_text(payload.get("discount_label"),120)
    if kind=='discount' and not discount:raise ValueError("discount_label_required")
    stamp=_now();existing=con.execute("SELECT code FROM commercial_coupons WHERE code=?",(code,)).fetchone();vals=(title,kind,plan,feature,trial,units,retention,discount,maximum,1 if bool(payload.get('active',True)) else 0,payload.get('starts_at'),payload.get('ends_at'),stamp,code)
    if existing:con.execute("UPDATE commercial_coupons SET title=?,kind=?,target_plan_id=?,target_feature_id=?,trial_days=?,unit_bonus=?,retention_days=?,discount_label=?,max_redemptions=?,active=?,starts_at=?,ends_at=?,updated_at=? WHERE code=?",vals)
    else:con.execute("INSERT INTO commercial_coupons(code,title,kind,target_plan_id,target_feature_id,trial_days,unit_bonus,retention_days,discount_label,max_redemptions,active,starts_at,ends_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(code,*vals[:-1],stamp))
    con.commit();return code


def redeem_coupon(con,user_id,code):
    code=_text(code,40).upper();c=con.execute("SELECT * FROM commercial_coupons WHERE code=? AND active=1",(code,)).fetchone()
    if not c:raise ValueError("coupon_not_available")
    now=_now_dt();start=_parse_time(c["starts_at"]) if c["starts_at"] else None;end=_parse_time(c["ends_at"]) if c["ends_at"] else None
    if start and now<start:raise ValueError("coupon_not_started")
    if end and now>end:raise ValueError("coupon_expired")
    if con.execute("SELECT id FROM commercial_coupon_redemptions WHERE code=? AND user_id=?",(code,int(user_id))).fetchone():raise ValueError("coupon_already_redeemed")
    used=int(scalar(con,"SELECT COUNT(*) FROM commercial_coupon_redemptions WHERE code=?",(code,)) or 0)
    if used>=int(c["max_redemptions"]):raise ValueError("coupon_redemption_limit_reached")
    kind=c["kind"];note=f"Coupon {code}: {c['title']}";result={"code":code,"kind":kind,"status":"applied"}
    if kind=='trial_plan':
        ends=(now+timedelta(days=int(c["trial_days"]))).isoformat();sid=grant_subscription(con,int(user_id),c["target_plan_id"],"complimentary",note,ends);result.update({"subscriptionId":sid,"endsAt":ends})
    elif kind=='feature_trial':
        ends=(now+timedelta(days=int(c["trial_days"]))).isoformat();result["access"]=grant_addon(con,user_id,c["target_feature_id"],"complimentary",limit_value=100 if c["target_feature_id"]==A072 else None,retain_days=365 if c["target_feature_id"]==A088 else None,note=note,ends_at=ends);result["endsAt"]=ends
    elif kind=='coaching_units':result["access"]=grant_addon(con,user_id,A072,"complimentary",limit_value=int(c["unit_bonus"]),note=note)
    elif kind=='retention_trial':
        ends=(now+timedelta(days=int(c["trial_days"]))).isoformat();result["access"]=grant_addon(con,user_id,A088,"complimentary",retain_days=int(c["retention_days"]),note=note,ends_at=ends);result["endsAt"]=ends
    elif kind=='discount':result.update({"status":"reserved","discountLabel":c["discount_label"],"billingBoundary":"Discount redemption reserves an offer only. It is not payment confirmation and grants no paid access by itself."})
    rid=f"cr_{secrets.token_hex(10)}";con.execute("INSERT INTO commercial_coupon_redemptions(id,code,user_id,status,note,created_at) VALUES(?,?,?,?,?,?)",(rid,code,int(user_id),result["status"],note,_now()));con.commit();result["redemptionId"]=rid;return result


def coupons_admin(con):
    rows=con.execute("SELECT * FROM commercial_coupons ORDER BY updated_at DESC,code").fetchall();out=[]
    for r in rows:
        d=dict(rowdict(r));d["redemptions"]=int(scalar(con,"SELECT COUNT(*) FROM commercial_coupon_redemptions WHERE code=?",(r["code"],)) or 0);out.append(d)
    return out


def save_customer_link(con,provider,customer_ref,user_id,target_type,target_id):
    provider=_text(provider,40).lower();customer_ref=_text(customer_ref,180);target_type=_text(target_type,20).lower();target_id=_text(target_id,80)
    if not provider or not customer_ref:raise ValueError("provider_customer_required")
    if target_type not in {"plan","feature"}:raise ValueError("invalid_billing_target_type")
    if target_type=='feature' and target_id not in ADDON_FEATURES:raise ValueError("unsupported_billing_feature")
    if target_type=='plan' and not con.execute("SELECT id FROM commercial_plans WHERE id=?",(target_id,)).fetchone():raise ValueError("billing_plan_not_found")
    if not con.execute("SELECT id FROM users WHERE id=? AND status='active'",(int(user_id),)).fetchone():raise ValueError("billing_user_not_found")
    stamp=_now();existing=con.execute("SELECT id FROM billing_customer_links WHERE provider=? AND customer_ref=? AND target_type=? AND target_id=?",(provider,customer_ref,target_type,target_id)).fetchone()
    if existing:
        lid=existing["id"];con.execute("UPDATE billing_customer_links SET user_id=?,updated_at=? WHERE id=?",(int(user_id),stamp,lid))
    else:
        lid=f"bl_{secrets.token_hex(10)}";con.execute("INSERT INTO billing_customer_links(id,provider,customer_ref,user_id,target_type,target_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",(lid,provider,customer_ref,int(user_id),target_type,target_id,stamp,stamp))
    con.commit();return lid


def expected_signature(raw_body,secret):return "sha256="+hmac.new(secret.encode(),raw_body,hashlib.sha256).hexdigest()

def verify_signature(raw_body,signature,secret=None):
    secret=secret if secret is not None else os.environ.get("EGM_BILLING_WEBHOOK_SECRET","")
    if not secret:return False
    return hmac.compare_digest(expected_signature(raw_body,secret),_text(signature,200))


def _provider_activate_plan(con,user_id,plan_id,provider_ref):
    stamp=_now();existing=con.execute("SELECT id FROM commercial_subscriptions WHERE user_id=? AND plan_id=? AND status='active'",(int(user_id),plan_id)).fetchone()
    if existing:
        sid=existing["id"];con.execute("UPDATE commercial_subscriptions SET source='provider_verified',source_ref=?,note=?,updated_at=? WHERE id=?",(provider_ref,"Verified provider event",stamp,sid))
    else:
        sid=f"sub_{secrets.token_hex(10)}";con.execute("INSERT INTO commercial_subscriptions(id,user_id,plan_id,status,source,source_ref,note,starts_at,ends_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(sid,int(user_id),plan_id,"active","provider_verified",provider_ref,"Verified provider event",stamp,None,stamp,stamp))
    return sid


def _provider_activate_feature(con,user_id,feature_id,provider_ref,payload):
    limit=int(payload.get("limit_value") or 0) or None;retain=int(payload.get("retain_days") or 0) or None
    if feature_id==A072 and (not limit or limit<1):limit=100
    if feature_id==A088 and (not retain or retain<30):retain=365
    stamp=_now();existing=con.execute("SELECT id FROM billing_addon_access WHERE user_id=? AND feature_id=? ORDER BY updated_at DESC LIMIT 1",(int(user_id),feature_id)).fetchone()
    if existing:
        aid=existing["id"];con.execute("UPDATE billing_addon_access SET status='active',source='provider_verified',source_ref=?,limit_value=?,retain_days=?,note=?,starts_at=?,ends_at=?,updated_at=? WHERE id=?",(provider_ref,limit,retain,"Verified provider event",stamp,payload.get("ends_at"),stamp,aid))
    else:
        aid=f"ba_{secrets.token_hex(10)}";con.execute("INSERT INTO billing_addon_access(id,user_id,feature_id,status,source,source_ref,limit_value,retain_days,note,starts_at,ends_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(aid,int(user_id),feature_id,"active","provider_verified",provider_ref,limit,retain,"Verified provider event",stamp,payload.get("ends_at"),stamp,stamp))
    return aid


def ingest_signed_provider_event(con,raw_body,signature,secret=None):
    if not verify_signature(raw_body,signature,secret):raise PermissionError("billing_signature_invalid")
    try:payload=json.loads(raw_body.decode("utf-8"))
    except Exception:raise ValueError("invalid_billing_event_json")
    event_id=_text(payload.get("event_id"),120);provider=_text(payload.get("provider"),40).lower();customer=_text(payload.get("customer_ref"),180);etype=_text(payload.get("event_type"),40).lower();status=_text(payload.get("status"),40).lower();occurred=_text(payload.get("occurred_at") or _now(),80)
    if not event_id or not provider or not customer:raise ValueError("billing_event_identity_required")
    if etype not in PROVIDER_EVENT_TYPES:raise ValueError("unsupported_billing_event_type")
    if con.execute("SELECT provider_event_id FROM billing_provider_events WHERE provider_event_id=?",(event_id,)).fetchone():return {"duplicate":True,"eventId":event_id}
    digest=hashlib.sha256(raw_body).hexdigest();link=con.execute("SELECT * FROM billing_customer_links WHERE provider=? AND customer_ref=? ORDER BY updated_at DESC LIMIT 1",(provider,customer)).fetchone();recon="unlinked";note="No customer link"
    if link:
        user_id=int(link["user_id"]);target_type=link["target_type"];target_id=link["target_id"];active=etype.endswith("_active")
        if (etype.startswith("plan_") and target_type!="plan") or (etype.startswith("feature_") and target_type!="feature"):
            recon="target_mismatch";note="Linked target type does not match provider event"
        else:
            if active:
                if target_type=="plan":_provider_activate_plan(con,user_id,target_id,event_id)
                else:_provider_activate_feature(con,user_id,target_id,event_id,payload)
            else:
                if target_type=="plan":con.execute("UPDATE commercial_subscriptions SET status='cancelled',updated_at=? WHERE user_id=? AND plan_id=? AND status='active'",(_now(),user_id,target_id))
                else:con.execute("UPDATE billing_addon_access SET status='revoked',updated_at=? WHERE user_id=? AND feature_id=? AND status='active'",(_now(),user_id,target_id))
            recon="reconciled";note=f"{target_type}:{target_id} -> user:{user_id}"
    con.execute("INSERT INTO billing_provider_events(provider_event_id,provider,customer_ref,event_type,event_status,amount,currency,occurred_at,payload_hash,verification_status,reconciliation_status,note,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(event_id,provider,customer,etype,status,_text(payload.get("amount"),80),_text(payload.get("currency"),12).upper(),occurred,digest,"signature_verified",recon,note,_now()));con.commit();return {"duplicate":False,"eventId":event_id,"verificationStatus":"signature_verified","reconciliationStatus":recon,"note":note}


def reconciliation_summary(con):
    rows=con.execute("SELECT * FROM billing_provider_events ORDER BY occurred_at DESC,created_at DESC LIMIT 200").fetchall();return {"schema":"egm.billing-reconciliation.v1","events":[dict(rowdict(r)) for r in rows],"summary":{"total":len(rows),"reconciled":sum(1 for r in rows if r["reconciliation_status"]=="reconciled"),"unlinked":sum(1 for r in rows if r["reconciliation_status"]=="unlinked"),"targetMismatch":sum(1 for r in rows if r["reconciliation_status"]=="target_mismatch")},"boundary":"Only signature-verified provider events may create provider_verified access. Manual owner actions cannot write this verification state."}


def billing_controls_status(con,user_id):
    return {"schema":"egm.billing-controls-status.v1","usageCoaching":addon_status(con,user_id,A072),"retentionInsights":addon_status(con,user_id,A086),"premiumRetention":addon_status(con,user_id,A088),"archives":retention_archives(con,user_id),"boundary":"Access state is separated from payment verification. Only signed provider reconciliation may assert provider_verified."}
