"""A095 signed reconciliation bridge for A082 marketplace and A083 white-label.

This extends the same billing_provider_events/customer-link ledger used by the core
A095 plan/feature reconciler. Only a valid HMAC-signed provider event may mark a
marketplace order or white-label license provider_verified.
"""
from __future__ import annotations

import hashlib
import json

from billing_controls import _now, _text, verify_signature
from marketplace_licensing import (
    get_marketplace_order,
    provider_cancel_marketplace_payment,
    provider_verify_marketplace_order,
    provider_verify_white_label,
    revoke_white_label,
)

COMMERCE_EVENT_TYPES={
    "marketplace_paid",
    "marketplace_reversed",
    "white_label_active",
    "white_label_cancelled",
}
COMMERCE_TARGET_TYPES={"marketplace_order","white_label"}


def save_commerce_customer_link(con,provider,customer_ref,user_id,target_type,target_id):
    provider=_text(provider,40).lower();customer_ref=_text(customer_ref,180);target_type=_text(target_type,30).lower();target_id=_text(target_id,100);user_id=int(user_id)
    if not provider or not customer_ref:raise ValueError("provider_customer_required")
    if target_type not in COMMERCE_TARGET_TYPES:raise ValueError("invalid_commerce_billing_target_type")
    if not con.execute("SELECT id FROM users WHERE id=? AND status='active'",(user_id,)).fetchone():raise ValueError("billing_user_not_found")
    if target_type=="marketplace_order":
        order=get_marketplace_order(con,target_id)
        if not order:raise ValueError("marketplace_order_not_found")
        if int(order["buyerUserId"])!=user_id:raise ValueError("marketplace_billing_user_mismatch")
    else:
        if target_id and target_id!=str(user_id):raise ValueError("white_label_billing_user_mismatch")
        target_id=str(user_id)
    stamp=_now();existing=con.execute("SELECT id FROM billing_customer_links WHERE provider=? AND customer_ref=? AND target_type=? AND target_id=?",(provider,customer_ref,target_type,target_id)).fetchone()
    if existing:
        lid=existing["id"];con.execute("UPDATE billing_customer_links SET user_id=?,updated_at=? WHERE id=?",(user_id,stamp,lid))
    else:
        import secrets
        lid=f"bl_{secrets.token_hex(10)}";con.execute("INSERT INTO billing_customer_links(id,provider,customer_ref,user_id,target_type,target_id,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",(lid,provider,customer_ref,user_id,target_type,target_id,stamp,stamp))
    con.commit();return lid


def ingest_signed_commerce_event(con,raw_body,signature,secret=None):
    if not verify_signature(raw_body,signature,secret):raise PermissionError("billing_signature_invalid")
    try:payload=json.loads(raw_body.decode("utf-8"))
    except Exception:raise ValueError("invalid_billing_event_json")
    event_id=_text(payload.get("event_id"),120);provider=_text(payload.get("provider"),40).lower();customer=_text(payload.get("customer_ref"),180);etype=_text(payload.get("event_type"),40).lower();status=_text(payload.get("status"),40).lower();occurred=_text(payload.get("occurred_at") or _now(),80)
    if not event_id or not provider or not customer:raise ValueError("billing_event_identity_required")
    if etype not in COMMERCE_EVENT_TYPES:raise ValueError("unsupported_commerce_billing_event_type")
    if con.execute("SELECT provider_event_id FROM billing_provider_events WHERE provider_event_id=?",(event_id,)).fetchone():return {"duplicate":True,"eventId":event_id}
    digest=hashlib.sha256(raw_body).hexdigest();link=con.execute("SELECT * FROM billing_customer_links WHERE provider=? AND customer_ref=? AND target_type IN ('marketplace_order','white_label') ORDER BY updated_at DESC LIMIT 1",(provider,customer)).fetchone();recon="unlinked";note="No commerce customer link"
    if link:
        user_id=int(link["user_id"]);target_type=link["target_type"];target_id=link["target_id"]
        expected="marketplace_order" if etype.startswith("marketplace_") else "white_label"
        if target_type!=expected:
            recon="target_mismatch";note="Linked commerce target type does not match provider event"
        else:
            if etype=="marketplace_paid":provider_verify_marketplace_order(con,target_id,event_id)
            elif etype=="marketplace_reversed":provider_cancel_marketplace_payment(con,target_id,event_id)
            elif etype=="white_label_active":provider_verify_white_label(con,user_id,event_id)
            elif etype=="white_label_cancelled":
                try:revoke_white_label(con,user_id,"Verified provider cancellation")
                except ValueError as exc:
                    if str(exc)!="white_label_license_not_found":raise
            recon="reconciled";note=f"{target_type}:{target_id} -> user:{user_id}"
    con.execute("INSERT INTO billing_provider_events(provider_event_id,provider,customer_ref,event_type,event_status,amount,currency,occurred_at,payload_hash,verification_status,reconciliation_status,note,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(event_id,provider,customer,etype,status,_text(payload.get("amount"),80),_text(payload.get("currency"),12).upper(),occurred,digest,"signature_verified",recon,note,_now()));con.commit()
    return {"duplicate":False,"eventId":event_id,"verificationStatus":"signature_verified","reconciliationStatus":recon,"note":note}
